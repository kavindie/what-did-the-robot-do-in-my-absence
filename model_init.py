# Import packages
import torch
import os
import re

#languagebind
from languagebind import LanguageBind, to_device, transform_dict, LanguageBindImageTokenizer

# videochat
from conversation import Chat
from video_chat2.utils.config import Config
from video_chat2.utils.easydict import EasyDict
from video_chat2.models.videochat2_it import VideoChat2_it
from peft import get_peft_model, LoraConfig, TaskType


# Import my implementations
from pre_process import process_video, combine_videos, convert_to_hms

# Greedy approach
def select_items(scores, similarities, num_items=10, similarity_threshold=0.5):
    # Sort the items by their scores in descending order
    sorted_scores, sorted_indices = torch.sort(scores, descending=True)

    selected_items = []
    for idx in sorted_indices:
        # Convert idx to integer
        idx = idx.item()

        # Check if the item is too similar to any of the already selected items
        if any(similarities[idx][i] > similarity_threshold for i in selected_items):
            continue

        # Add the item to the list of selected items
        selected_items.append(idx)

        # Stop if we have selected the desired number of items
        if len(selected_items) == num_items:
            break

    return selected_items

class Models:
    def __init__(self, video_paths=[], fps_required=1):
        self.video_paths = video_paths
        config_file = "video_chat2/configs/config.json"
        cfg = Config.from_file(config_file)
        device = cfg.device

        self.device = torch.device(device)

        # LanguageBind
        print('Initializing LanguageBind')
        clip_type = {
            'video': 'LanguageBind_Video_FT',  # also LanguageBind_Video
            'audio': 'LanguageBind_Audio_FT',  # also LanguageBind_Audio
            'thermal': 'LanguageBind_Thermal',
            'image': 'LanguageBind_Image',
            'depth': 'LanguageBind_Depth',
        }
        self.LanguageBindModel = LanguageBind(clip_type=clip_type, cache_dir='./cache_dir')
        self.LanguageBindModel = self.LanguageBindModel.to(self.device)
        self.LanguageBindModel.eval()
        pretrained_ckpt = f'LanguageBind/LanguageBind_Image'
        self.tokenizer = LanguageBindImageTokenizer.from_pretrained(pretrained_ckpt, cache_dir='./cache_dir/tokenizer_cache_dir')
        self.modality_transform = {c: transform_dict[c](self.LanguageBindModel.modality_config[c]) for c in clip_type.keys()}
        print("LanguageBind loaded")

        #videochat2
        print('Initializing VideoChat')
        cfg.model.vision_encoder.num_frames = 4
        model = VideoChat2_it(config=cfg.model)
        model = model.to(self.device)

        peft_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM, inference_mode=False, 
            r=16, lora_alpha=32, lora_dropout=0.
        )
        model.llama_model = get_peft_model(model.llama_model, peft_config)
        state_dict = torch.load("./videochat2_7b_stage3.pth", self.device)
        if 'model' in state_dict.keys():
            msg = model.load_state_dict(state_dict['model'], strict=False)
        else:
            msg = model.load_state_dict(state_dict, strict=False)
        print(msg)
        model = model.eval()
        self.VideoChat2Model = model

        self.chat = Chat(self.VideoChat2Model, device=self.device)
        
        self.chat_state = EasyDict({
            "system": "",
            "roles": ("Human", "Assistant"),
            "messages": [],
            "sep": "###"
        })
        self.img_list = []

        print('Initialization Finished')

        print("Now loading video data")
        self.output_dirs = []
        self.all_inputs = {}
        for i, vid_path in enumerate(video_paths):
            mini_video_files, images, output_dir = process_video(vid_path, fps_required=fps_required)
            # The processed frames and mini videos will be stored in the vids folder under output_dir/frames and output_dir/mini_videos. 

            self.output_dirs.append(output_dir)
            def load_or_gen_and_save(path, fun):
                if os.path.exists(path):
                    value = torch.load(path, map_location=self.device)
                else:
                    value = fun()
                    # saving the encoded frames and video in image_enc.pth and video_enc.pth to reduce recomputation
                    torch.save(value, path)
                return value
            
            self.all_inputs[f'{i}_image'] = load_or_gen_and_save(f'{self.output_dirs[i]}/image_enc.pth', lambda: to_device(self.modality_transform['image'](images), self.device))
            self.all_inputs[f'{i}_video'] = load_or_gen_and_save(f'{self.output_dirs[i]}/video_enc.pth', lambda: to_device(self.modality_transform['video'](mini_video_files), self.device))


    def queryLanguageBindImage(self, text, m=6, vid_num=1, mode='image'):
        language = [text]
        inputs = {
            'image' : self.all_inputs[f'{vid_num}_image'],
        }
        inputs['language'] = to_device(self.tokenizer(language, max_length=77, padding='max_length',
                                                    truncation=True, return_tensors='pt'), self.device)
        
        with torch.no_grad():
            embeddings = self.LanguageBindModel(inputs)
        
        v = embeddings['image'] @ embeddings['language'].T
        s = torch.softmax(v, dim=0)
        s_flattened = s.view(-1)

        # greedy approach
        xf = v
        probabilities_xf = s_flattened
        ff = embeddings[mode] @ embeddings[mode].T
        normalized_ff = (ff - ff.min()) / (ff.max() - ff.min())
        normalized_ff.fill_diagonal_(float('-inf')) # will be most similar to itself
        probabilities_ff = torch.nn.functional.softmax(normalized_ff, dim=1)
        indices_s = torch.tensor(select_items(probabilities_xf, probabilities_ff, num_items=m))
        indices_s = indices_s.sort().values.tolist()
        top_results = [f'{self.output_dirs[vid_num]}/frames/frame_{i}.jpg' for i in indices_s]
        fps = int(self.output_dirs[vid_num].split('_')[-1])
        times = [convert_to_hms(i/fps) for i in indices_s]

        return top_results, times

    def queryLanguageBindVideo(self, text, top_k=6, vid_num=0, mode='video'):
        language = [text]
        inputs = {
            'video' : self.all_inputs[f'{vid_num}_video'],
        }
        inputs['language'] = to_device(self.tokenizer(language, max_length=77, padding='max_length',
                                                    truncation=True, return_tensors='pt'), self.device)
        with torch.no_grad():
            embeddings = self.LanguageBindModel(inputs)
        
        v = embeddings['video'] @ embeddings['language'].T
        s = torch.softmax(v, dim=0)
        s_flattened = s.view(-1)

        _, indices_s = torch.topk(s_flattened, top_k)
        
        results = [f'{self.output_dirs[vid_num]}/mini_videos/mini_video_{i}.mp4' for i in indices_s.sort().values.tolist()]
        if not os.path.exists(dir:=os.path.join(self.output_dirs[vid_num], 'prompts')):
            os.makedirs(dir)
        filename = re.sub(r'[^\w ]','', text)
        output_video_file = os.path.join(dir, f'{filename}.mp4')

        combine_videos(results, output_video_file)
        return output_video_file

    def queryLanguageBindVideoChat2Video(self, text, top_k=6, vid_num=2):
        output_video_file = self.queryLanguageBindVideo(text=text, top_k=top_k, vid_num=vid_num)
        llm_message, self.img_list, self.chat_state = self.chat.upload_video(output_video_file, self.chat_state, self.img_list, num_segments=100)
        self.chat_state = self.chat.ask(text, self.chat_state)
        llm_message, _, _ = self.chat.answer(conv=self.chat_state, img_list=self.img_list, max_new_tokens=1000, num_beams=1, temperature=0.3) 
        llm_message = llm_message.replace("<s>", "") # handle <s>
        return llm_message

    def queryVideoChat2(self, text, chatbot, vid_num=2):
        llm_message = self.queryLanguageBindVideoChat2Video(text, top_k=6, vid_num=vid_num)
        chatbot = chatbot + [[text, None]]
        chatbot[-1][1] = llm_message
        print(f"Answer: {llm_message}")
        return "", chatbot
    
    def resetchat(self):
        self.chat_state = EasyDict({
            "system": "",
            "roles": ("Human", "Assistant"),
            "messages": [],
            "sep": "###"
        })
        self.img_list = []



