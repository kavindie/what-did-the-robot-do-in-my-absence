# Import packages
from functools import partial
import random
import gradio as gr
import csv
import time
import os

# Import my implementations
from pre_process import convert_to_hms

debug = False # Make this true if you want to debug the code - less pages
model_test = True # Make this true if you want to load models to generate query-driven summaries real-time
generic = False # Are you running hte G pipeline or Q pipeline?

# Make sure you have the long videos in the vid folder

# control(C) = long video
raw_control_placeholder = 'vids/{}.mp4' # Insert the long video file path here

# video (V) summary - the long video to generate this from
raw_video_placeholder = 'vids/{}.mp4' # Insert the long video file path here
generic_summary_video_placeholder = 'vids/{}.mp4' # Pre computed generic summary video (using STVT)

# Storyboard/gallery (S) summary - the long video to generate this from
raw_storyboard_placeholder = 'vids/{}.mp4'
generic_storyboard_img_list = [...] # Frame numbers corresponding to the selected generic keyframes (using STVT)
generic_summary_storyboard_placeholder = '.../Images' # Path to computed generic summary keyframes (using STVT)

# Text (T) summary - the long video to generate this from
raw_text_placeholder = 'vids/{}.mp4' # Insert the long video file path here

if model_test:
    from model_init import Models
    video_paths = [raw_video_placeholder, 
                   raw_storyboard_placeholder, 
                   raw_text_placeholder,
                   ] 
    # Please note the order you give the videos matter. 
    # Currently 0:raw_video_placeholder, 1:raw_storyboard_placeholder, 2:raw_text_placeholder
    # If another format is followed you need to change the vid_num parameter in model_init.py
    models = Models(video_paths=video_paths, fps_required=1) # At what frame rate do you want the video to be processed
else:
    models = None

print("Models are initialised")

participant_id = int(time.time())
start_times = {}
times_spent = {}
beginning = time.time()
urls = {}

familiarity_choices = ["Not Familiar at all", "Somewhat familiar", "Moderately familiar", "Quite familiar", "Very familiar"]
trust_choices = ["Strongly distrust", "Distrust", "Neutral", "Trust ", "Strongly trust"]
frequency_choices = ["Never", "Rarely", "Sometimes", "Often", "Daily"]

headers = ["participant_id"]
data = [participant_id]
if generic:
   folder = os.path.join(os.getcwd(), 'ParticipantData/Generic', str(participant_id))
else:
   folder = os.path.join(os.getcwd(), 'ParticipantData/Query', str(participant_id))
os.mkdir(folder)
filename = f'{folder}/answers.csv'

def get_inputs(node, inputs, main_tab_id):
    # Check if node is a Radio or Slider
    if isinstance(node, (gr.Radio, gr.Slider, gr.Textbox)): 
        if node.label:
            if node.label != 'User Query':
                inputs.append(node) 
                if node.label not in headers:
                    headers.append(f"{main_tab_id}: {node.label}")

    # If node has children, recurse on each child
    if hasattr(node, 'children'):
        for child in node.children:
            get_inputs(child, inputs, main_tab_id)

def chat_output_video(text, page_title):
    global models
    print(text, page_title)
    with open(f'{folder}/{page_title}_queries.txt', 'a') as file:
        print(f"{text=}", file=file)
    s_time = time.time()
    
    top_video_path = models.queryLanguageBindVideo(text, vid_num=0, mode='video')
    
    with open(f'{folder}/{page_title}_video4queries.txt', 'a') as file:
        print(f"{text=}, {top_video_path=}", file=file)
    e_time = time.time()
    duration = e_time - s_time
    with open(f'{folder}/{page_title}_timetaken.txt', 'a') as file:
        print(f"{duration=}", file=file)
    return top_video_path

def chat_output_image(text, page_title):
    global models
    print(text, page_title)
    with open(f'{folder}/{page_title}_queries.txt', 'a') as file:
        print(f"{text=}", file=file)
    s_time = time.time()
    
    top_images, times = models.queryLanguageBindImage(text, m=4, vid_num=1, mode='image')
    
    with open(f'{folder}/{page_title}_images4queries.txt', 'a') as file:
        print(f"{text=}, {top_images=}", file=file)
    e_time = time.time()
    duration = e_time - s_time
    with open(f'{folder}/{page_title}_timetaken.txt', 'a') as file:
        print(f"{duration=}", file=file)
    return list(zip(top_images, times))

def video_chat2_ask_answer(text, chatbot, page_title):
    global models
    with open(f'{folder}/{page_title}_queries.txt', 'a') as file:
        print(f"{text=}", file=file)
    s_time = time.time()

    text_empty, chatbot = models.queryVideoChat2(text, chatbot, vid_num=2)
    
    with open(f'{folder}/{page_title}_text4queries.txt', 'a') as file:
        print(f"{text=}, {chatbot=}", file=file)
    e_time = time.time()
    duration = e_time - s_time
    with open(f'{folder}/{page_title}_timetaken.txt', 'a') as file:
        print(f"{duration=}", file=file)
    return text_empty, chatbot

def played_video(title):
  def played_video(evt: gr.EventData):
    with open(f'{folder}/interacted.txt', 'a') as file:
        print(f"{title} is played", file=file)
  return played_video

def selected_gallery(title):
  def selected_gallery(evt: gr.SelectData):
    with open(f'{folder}/interacted.txt', 'a') as file:
        print(f"{title} selected {evt.value['image']['orig_name']}", file=file)
  return selected_gallery

def selected_video_speed(title):
  def selected_video_speed(evt: gr.SelectData):
    with open(f'{folder}/interacted.txt', 'a') as file:
        print(f"{title} speed {evt.value}", file=file)
  return selected_video_speed


def gave_consent(title):
   pass


PAGE = 0
def page_indicator():
    global PAGE, N_PAGES
    assert PAGE is not None
    assert N_PAGES
    PAGE += 1
    return gr.Markdown(f"You are on page {PAGE}/{N_PAGES}")


## Defining the questions for each task and usability questions

# Questions for video summary task
def vid_qns():
    return [
    gr.Markdown("What objects did you observe in the following list and how many of each? Please refer the list of images [here](<link_to_object_images>)"),
    gr.Radio(label="Blue Barrel", choices=["0", "1", "2", ">2","Not sure"]), #2
    gr.Radio(label="Dummy (not a real person) wearing a green high-vis jacket", choices=["0", "1", "2", ">2","Not sure"]), #0
    gr.Radio(label="White Helmet", choices=["0", "1", "2", ">2","Not sure"]), #1
    gr.Slider(label="How confident are you about the above answers?", info="1- Not confident at all, 10- Very confident", minimum=1, maximum=10, interactive=True, step=1), 
    gr.Markdown("Select the most appropriate answer as per your understanding of the video. Please refer the list of images [here](<link_to_object_images>)"),
    gr.Radio(label="Who enters the tunnel before you?", 
        choices=["No one", "1 Spot", "2 Spots", "1 ATR", "2 ATRs", "1 spot and 1 ATR", "2 spots and 1 ATR", "1 spot and 2 ATRs", "Not sure"]), #No one
    gr.Radio(label="Do you climb any stairs during the run?", choices=["Yes - successfully", "Yes - unsuccessfully", "No stairs were found", "Not sure"]), #Yes - successfully
    gr.Radio(label="Do you knock down a door while trying to pass through it?", choices=["Yes", "No", "Not sure"]), #No
    gr.Slider(label="How confident are you about the above answers?", info="1- Not confident at all, 10- Very confident", minimum=1, maximum=10, interactive=True, step=1 ),
    ]

# Questions for storyboard summary task
def img_qns():
   return [
    gr.Markdown("What objects did you observe in the following list and how many of each? Please refer the list of images [here](<link_to_object_images>)"),
    gr.Radio(label="Artificial Bamboo Tree", choices=["0", "1", "2", ">2","Not sure"]), #1
    gr.Radio(label="White Helmet", choices=["0", "1", "2", ">2","Not sure"]), #0
    gr.Radio(label="Black Barrel", choices=["0", "1", "2", ">2","Not sure"]), #>2
    gr.Slider(label="How confident are you about the above answers?", info="1- Not confident at all, 10- Very confident", minimum=1, maximum=10, interactive=True, step=1), 
    gr.Markdown("Select the most appropriate answer as per your understanding of the video. Please refer the list of images [here](<link_to_object_images>)"),
    gr.Radio(label="Who enters the tunnel before you?", 
        choices=["No one", "1 Spot", "2 Spots", "1 ATR", "2 ATRs", "1 spot and 1 ATR", "2 spots and 1 ATR", "1 spot and 2 ATRs", "Not sure"]), #1 spot and 1 ATR
    gr.Radio(label="Do you encounter a path blocked by rocks?", choices=["Yes", "No", "Not sure"]), #No
    gr.Radio(label="Do you knock down a door while trying to pass through it?", choices=["Yes", "No", "Not sure"]), #Yes
    gr.Slider(label="How confident are you about the above answers?", info="1- Not confident at all, 10- Very confident", minimum=1, maximum=10, interactive=True, step=1 ),
   ]

# Questions for text summary task
def text_qns():
   return [
    gr.Markdown("What objects did you observe in the following list and how many of each? Please refer the list of images [here](<link_to_object_images>)"),
    gr.Radio(label="Blue Rope Bundle", choices=["0", "1", "2", ">2","Not sure"]), #0
    gr.Radio(label="Fire Extinguisher", choices=["0", "1", "2", ">2","Not sure"]), #>2
    gr.Radio(label="Drill", choices=["0", "1", "2", ">2","Not sure"]), #2
    gr.Slider(label="How confident are you about the above answers?", info="1- Not confident at all, 10- Very confident", minimum=1, maximum=10, interactive=True, step=1), 
    gr.Markdown("Select the most appropriate answer as per your understanding of the video. Please refer the list of images [here](<link_to_object_images>)"),
    gr.Radio(label="In the first three-way junction you get inside the tunnel, which direction do you choose to explore?", 
        choices=["Left", "Middle", "Right", "Not sure"]), #Middle
    gr.Radio(label="Do you encounter a path blocked by rocks?", choices=["Yes", "No", "Not sure"]), #Yes
    gr.Radio(label="Do you climb any stairs during the run?", choices=["Yes", "No", "Not sure"]), #No
    gr.Slider(label="How confident are you about the above answers?", info="1- Not confident at all, 10- Very confident", minimum=1, maximum=10, interactive=True, step=1 ),
   ]
   

def usability_qns():
  return [
    gr.Markdown("""How did you find the system? 
                1 = Strongly disagree, 2 = Disagree, 3 = Neutral, 4 = Agree, 5 = Strongly agree"""),
    gr.Slider(minimum=1, maximum=5, value=3, interactive=True, step=1, label="I think that I would like to use this system frequently."),
    gr.Slider(minimum=1, maximum=5, value=3, interactive=True, step=1, label="I found the system unnecessarily complex."),
    gr.Slider(minimum=1, maximum=5, value=3, interactive=True, step=1, label="I thought the system was easy to use."),
    gr.Slider(minimum=1, maximum=5, value=3, interactive=True, step=1, label="I think that I would need the support of a technical person to be able to use this system."),
    gr.Slider(minimum=1, maximum=5, value=3, interactive=True, step=1, label="I found the various functions in this system were well integrated."),
    gr.Slider(minimum=1, maximum=5, value=3, interactive=True, step=1, label="I thought there was too much inconsistency in this system."),
    gr.Slider(minimum=1, maximum=5, value=3, interactive=True, step=1, label="I would imagine that most people would learn to use this system very quickly."),
    gr.Slider(minimum=1, maximum=5, value=3, interactive=True, step=1, label="I found the system very cumbersome to use."),
    gr.Slider(minimum=1, maximum=5, value=3, interactive=True, step=1, label="I felt very confident using the system."),
    gr.Slider(minimum=1, maximum=5, value=3, interactive=True, step=1, label="I needed to learn a lot of things before I could get going with this system."),
  ]


## Defining the pages

# Consent page
def consent_page(title="Research Participant Consent Form"):
  with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    gr.Markdown("""
        Please insert your relevant participant consent form here.
    """)
  return page

generic_part = "an AI-generated summary to assist in answering questions on the right"
query_part = "an interface to query an AI model for answers to questions on the right"

# Instruction page
def inst_page(title="Instructions for the User"):
  with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    gr.Markdown(f"""
                A robot has been exploring an underground area and has captured a video of its journey.
                You'll be viewing the scene from the robot's front perspective, and asked questions about the robot's actions or environment.
                Each video is 40 minutes long: too time-consuming for you to watch in it's entirety.
                You will be provided with various AI tools to help you complete the task quickly and accurately.

                You can see your progress on the top of each page: 'You are on page X/{N_PAGES}'.
                You are not permitted to record the sessions, or download or share the video links.

                On the next page, we will ask some questions to understand your familiarity with robotics, robot operating environments, and video summarization models.

                In subsequent pages, you will presented with a video and asked to answer questions.
                The left side will show the video, accompanied by {generic_part if generic else query_part}.
                Your task is to answer these questions, and you're encouraged to use the AI tool. Instructions on how to use it will be provided on the relevant page.
                On pages with the AI tool, you are free to play or ignore the full 40 minute video at the bottom of the page.

                Some questions relate to a number of objects visible in the environment,
                a table showing what the objects may look like is given
                [here](<link_to_object_images>).

                Please remember that each page will feature a different video, unrelated to the videos on previous pages.
                The questions may also change from page to page.
                Altogether, there will be 4 main parts which will be presented in a random order:
                * Answering based on the **original video**.
                * Answering based on an AI-generated **video** summary.
                * Answering based on an AI-generated **image** summary.
                * Answering based on an AI-generated **text** summary.

                After each, there will be a usability page asking your thoughts about using each system.

                Finally, the last page asks your preferences between the 3 output modes of the AI tools.

                **This task is time-sensitive, so we expect you to answer the questions as quickly and accurately as possible.**
                You **are not** to watch the long videos from start to end: this would take 40 minutes x 4 = 2 hours and 40 minutes.
                Please spend less than 15 minutes on each part.
                """)
  return page

# Familiarity page
def familiarity_page(title="Familiarity Questions"):
  with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    gr.Radio(label="On a scale of from a novice to an expert, how would you rate your expertise in operating robots?", choices=["Novice", "Advanced Beginner", "Competent", "Proficient", "Expert"])
    gr.Radio(label="How familiar are you with environments such as underground tunnels?", choices=familiarity_choices)
    gr.Radio(label="How familiar are you with the SubT (it is okay to not know this word) environment?", choices=familiarity_choices)
    gr.Radio(label="How frequently do you interact with robots in your daily life (e.g., at work, at home)?", choices=frequency_choices)
    gr.Radio(label="How often do you watch videos for educational or informational purposes?", choices=frequency_choices)
    gr.Radio(label="How would you rate your familiarity with the concept of video summarization?", choices=familiarity_choices)
    gr.Radio(label="How familiar are you with interactive models that summarize videos based on questions?", choices=familiarity_choices)
    gr.Radio(label="How frequently do you utilize interactive models such as ChatGPT, Gemini, Claude?", choices=frequency_choices)
    gr.Radio(label="How much do you trust the output of such models?", choices=trust_choices)
  return page

# Usability page
def usability_page(title):
  with gr.Blocks(title=f"{title} Usability") as page:
    gr.Markdown(f"# {title} Usability")
    page_indicator()
    with gr.Column():
        gr.Markdown("What did you think about the system?")
        usability_qns()
        gr.Textbox(label="Do you have any further comments about the system (optional)?", value=None)
  return page

# Control (C) page
def raw_vid_page(title="Original Video"):
  with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("""Here you can find the video collected by the robot during its exploration. You can play at your preferred speed. 
                        Please refrain from using the speed controls in the YouTube.""")
            # Each tab is for a different speed setting
            # You can do this in two ways. One way is to upload to youtube and give the youtube link. The other is to give the placeholder of the video

            with gr.Tab(label='Original Speed') as tab: # Original speed
              tab.select(selected_video_speed(page.title))
              gr.HTML('<iframe width="540" height="315" src="<Link to youtube video>" title="YouTube video player" frameborder="0" allow="encrypted-media" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>')
              #  gr.Video(value=f"{raw_control_placeholder}", show_label=False, show_download_button=False)
            with gr.Tab(label='x 2 Speed') as tab: # x2 speed
              tab.select(selected_video_speed(page.title))
              gr.HTML('<iframe width="540" height="315" src="<Link to youtube video>" title="YouTube video player" frameborder="0" allow="encrypted-media" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>')
              #  gr.Video(value=f"<path to video with x2 speed>", show_label=False, show_download_button=False)
            with gr.Tab(label='x 4 Speed') as tab: # x4 speed
              tab.select(selected_video_speed(page.title))
              gr.HTML('<iframe width="540" height="315" src="<Link to youtube video>" title="YouTube video player" frameborder="0" allow="encrypted-media" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>')
              #  gr.Video(value=f"<path to video with x4 speed>", show_label=False, show_download_button=False)
            with gr.Tab(label='x 8 Speed') as tab: # x8 speed
              tab.select(selected_video_speed(page.title))
              gr.HTML('<iframe width="540" height="315" src="<Link to youtube video>" title="YouTube video player" frameborder="0" allow="encrypted-media" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>')
              #  gr.Video(value=f"<path to video with x8 speed>", show_label=False, show_download_button=False)
                       
        with gr.Column(scale=1, visible=True):
           gr.Markdown("Adding space", visible=False)

        with gr.Column(scale=3):
            gr.Markdown("What objects did you observe in the following list and how many of each? Please refer the list of images [here](<link_to_object_images>)"),
            gr.Radio(label="Red Backpack", choices=["0", "1", "2", ">2","Not sure"]), #1
            gr.Radio(label="Fire Extinguisher", choices=["0", "1", "2", ">2","Not sure"]), #2
            gr.Radio(label="Green high-vis jackets (not worn by a person/dummy)", choices=["0", "1", "2", ">2","Not sure"]), #0
            gr.Slider(label="How confident are you about the above answers?", info="1- Not confident at all, 10- Very confident", minimum=1, maximum=10, interactive=True, step=1), 
            gr.Markdown("Select the most appropriate answer as per your understanding of the video. Please refer the list of images [here](<link_to_object_images>)"),
            gr.Radio(label="At the first three-way junction, which direction does the robot ahead of you go through?", 
            choices=["Left", "Middle", "Right", "No robot ahead of me","Not sure"]), #Left
            gr.Radio(label="Do you encounter a path blocked by rocks?", choices=["Yes", "No", "Not sure"]), #No
            gr.Radio(label="Do you climb any stairs during the run?", choices=["Yes - successfully", "Yes - unsuccessfully", "No stairs were found", "Not sure"]), #Yes - unsuccessfully
            gr.Slider(label="How confident are you about the above answers?", info="1- Not confident at all, 10- Very confident", minimum=1, maximum=10, interactive=True, step=1 ),   
  return page

# Generic Video (GV) page
def gen_video_page(title="Generic Summary Video"):
  with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("""
                To help you with the task, the model has produced a summary video of major events that occurred during the run. 

                Please be aware that the model isn't perfect and may make errors. 
                
                **Please note that this is a time-critical task. Therefore, the expectation is for you to answer the questions as quickly and accurately as possible**
            """)
            gr.Video(value=f"{generic_summary_video_placeholder}", show_label=False, show_download_button=False)
            gr.Markdown("""
                Below you can find the original video of what happened. 
                It will take a couple of seconds to load.
                """)
            # You might need to have a low res video or a uploaded video to youtube to load fast
            gr.Video(value=f"{raw_video_placeholder}", show_label=False, show_download_button=False).play(played_video(f"{page.title} long video"))
            
        with gr.Column(scale=1, visible=True):
           gr.Markdown("Adding space", visible=False)

        with gr.Column(scale=3):
            vid_qns()
  return page

# Generic Storyboard (GS) page
def gen_gallery_page(title="Generic Summary Gallery"):
  with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("""
                To help you with the task, the following 24 images are selected by the model as the most critical. 
                The images are given in chronological order. 
                The image label is the time at which you can find it in the below video. 
                To navigate through the gallery, click the x on the top right of the image. You can click on each image in the gallery to enlarge it. 

                Please be aware that the model isn't perfect and may make errors. 

                **Please note that this is a time-critical task. Therefore, the expectation is for you to answer the questions as quickly and accurately as possible**
            """) 
            gallery = gr.Gallery(
                value=[(f"{generic_summary_storyboard_placeholder}/frame_{k}.jpg", convert_to_hms(k/15)) for k in generic_storyboard_img_list], 
                columns=4, rows=6, preview=True, show_download_button=False, show_share_button=False).select(selected_gallery(f"{page.title} gallery"))
            gr.Markdown("""
                        Below you can find the original video of what happened. 
                        It will take a couple of seconds to load.
                        """)
            # You might need to have a low res video or a uploaded video to youtube to load fast
            gr.Video(value=f"{raw_storyboard_placeholder}", show_label=False, show_download_button=False).play(played_video(f"{page.title} long video"))

        with gr.Column(scale=1, visible=True):
           gr.Markdown("Adding space", visible=False)

        with gr.Column(scale=3):
            img_qns()

  return page

# Generic Text (GT) page
def gen_text_page(title="Generic Summary Text"):
  with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("""
                To help you with the task, the model has produced a text-based summary of the events that occurred during the run. 

                Please be aware that the model isn't perfect and may make errors. 

                **Please note that this is a time-critical task. Therefore, the expectation is for you to answer the questions as quickly and accurately as possible**
            """)
            gr.Markdown("""
                        <span style='color:green;'>The video shows the path taken by a robot moving through an underground tunnel. 
                        The robot moves forward and sees various objects along the way. 
                        These objects are of different colors and shapes and are located in different parts of the tunnel. 
                        The objects seen include carts, lamps, red, green, blue and yellow. 
                        There are three carts, three lamps, two green objects, one red object, one blue object and one yellow object. 
                        The robot is seen moving forward and taking a left turn, moving forward and taking a right turn, and finally moving forward again. 
                        Overall, the video shows the robot's journey through the underground tunnel.</span>
                        """)
            
            gr.Markdown("""
                Below you can find the original video of what happened. 
                It will take a couple of seconds to load.
                """)
            # You might need to have a low res video or a uploaded video to youtube to load fast
            gr.Video(value=f"{raw_text_placeholder}", show_label=False, show_download_button=False).play(played_video(f"{page.title} long video"))

        with gr.Column(scale=1, visible=True):
           gr.Markdown("Adding space", visible=False)

        with gr.Column(scale=3):
            text_qns()

  return page

# Query Video (QV) page
def query_video_page(title="Query Summary Video"):
  with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("""
                To help you with the task, you can use the provided interface to ask a model to generate the answers for you. 
                Just type your question into the box labeled ‘User Query', and either click 'Submit' or press Enter. 
                The model will produce a short video that is most relevant to your query as per the model. 
                You can drag the ‘User Query' box from the bottom right to make it bigger. 
                The 'Clear' button will refresh the Video Output.

                Please be aware that the model isn't perfect and may make errors. 

                **Please note that this is a time-critical task. Therefore, the expectation is for you to answer the questions as quickly and accurately as possible**
            """)
            with gr.Row():
                gr.Interface(
                    fn=partial(chat_output_video, page_title=page.title),
                    inputs =[
                        gr.Text(label="User Query"),
                    ],
                    outputs = [
                        gr.Video(label="Video Output", show_download_button=False), 
                    ],
                    allow_flagging='never',
                )
            gr.Markdown("""
                Below you can find the original video of what happened. 
                It will take a couple of seconds to load.
                """)
            # You might need to have a low res video or a uploaded video to youtube to load fast
            gr.Video(value=f"{raw_video_placeholder}", show_label=False, show_download_button=False).play(played_video(f"{page.title} long video"))
        
        with gr.Column(scale=1, visible=True):
           gr.Markdown("Adding space", visible=False)

        with gr.Column(scale=3):
            vid_qns()

  return page

# Query Storyboard (QS) page
def query_gallery_page(title="Query Summary Gallery"):
  with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("""
                To help you with the task, you can use the provided interface to ask a model to generate the answers for you. 
                Just type your question into the box labeled ‘User Query', and either click 'Submit' or press Enter. 
                The model will produce a gallery of 4 images. 
                These 4 images are the most relevant to your query as per the model. The images are given in chronological order.
                The image label is the time at which you can find it in the below video. 
                To navigate through the gallery, click the x on the top right of the image. You can click on each image in the gallery to enlarge it. 

                Please be aware that the model isn't perfect and may make errors. 

                **Please note that this is a time-critical task. Therefore, the expectation is for you to answer the questions as quickly and accurately as possible**
                """)
            with gr.Row():
                gr.Interface(
                    fn=partial(chat_output_image, page_title=page.title),
                    inputs =[
                        gr.Text(label="User Query")
                    ],
                    outputs = [
                        gr.Gallery(columns=[2], rows=[2], label="Image Output", object_fit="contain", height="auto", preview=True, show_download_button=False, show_share_button=False),
                    ],
                    allow_flagging='never',
                )
            gr.Markdown("""
                Below you can find the original video of what happened. 
                It will take a couple of seconds to load.
                """)
            # You might need to have a low res video or a uploaded video to youtube to load fast
            gr.Video(value=f"{raw_storyboard_placeholder}", show_label=False, show_download_button=False).play(played_video(f"{page.title} long video"))

        with gr.Column(scale=1, visible=True):
           gr.Markdown("Adding space", visible=False)

        with gr.Column(scale=3):
            img_qns()

  return page

# Query Text (QT) page
def query_text_page(title="Query Summary Text"):
  with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("""
                        To help you with the task, you can use the provided interface to ask a model to generate the answers for you. 
                        Just type your question into the box labeled ‘User Query', and either click 'Submit' or press Enter.  
                        The model will produce a text answer for you. 
                        You can drag the ‘User Query' box from the bottom right to make it bigger.
                        The 'Clear' button will refresh the chat interface.  

                        Please be aware that the model isn't perfect and may make errors. 

                        **Please note that this is a time-critical task. Therefore, the expectation is for you to answer the questions as quickly and accurately as possible**
                        """)
            with gr.Row():
                with gr.Column(variant="panel"):
                    text_input = gr.Text(label='User Query')
                    chatbot = gr.Chatbot(label='Chat Interface', render=False)
                    with gr.Row():
                        if model_test:
                           if debug:
                            gr.ClearButton([text_input, chatbot])
                           else: 
                            gr.ClearButton([text_input, chatbot]).click(models.resetchat)
                        else:
                           gr.ClearButton([text_input, chatbot])
                        submit_btn = gr.Button("Submit", variant="primary")
                    text_input.submit(partial(video_chat2_ask_answer, page_title=page.title), [text_input, chatbot], [text_input, chatbot])
                    submit_btn.click(partial(video_chat2_ask_answer, page_title=page.title), [text_input, chatbot], [text_input, chatbot])
                with gr.Column(variant="panel"):
                    chatbot.render()
            gr.Markdown("""
                Below you can find the original video of what happened. 
                It will take a couple of seconds to load.
                """)
            # You might need to have a low res video or a uploaded video to youtube to load fast
            gr.Video(value=f"{raw_text_placeholder}", show_label=False, show_download_button=False).play(played_video(f"{page.title} long video"))

        with gr.Column(scale=1, visible=True):
           gr.Markdown("Adding space", visible=False)

        with gr.Column(scale=3):
           text_qns()
  return page

# Post-study page
def summary_page(title="Few extra questions"):
  with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    gr.Markdown("### Please answer the following questions regarding your experience with the AI tools.")
    gr.Radio(label="From the 3 output modes which one did you prefer the best?", choices=["Video", "Text", "Image Gallery"])
    gr.Textbox(label="Why? (optional)", value=None)
    gr.Radio(label="From the 3 output modes which one did you prefer the least?", choices=["Video", "Text", "Image Gallery"])
    gr.Textbox(label="Why? (optional)", value=None)
    gr.Radio(label="Do you think the AI tools helped you in task completion?", choices=["Yes", "No"])
    gr.Textbox(label="Why? (optional)", value=None)
  return page

# Show correct answers to users
def load_answers():
    user_ans = []
    if debug:
        list_of_files = ['Original Video.csv']
    else:
        a = "Generic" if generic else "Query"
        list_of_files = ['Original Video.csv', f'{a} Summary Video.csv', f'{a} Summary Text.csv', f'{a} Summary Gallery.csv'] 
    for f in list_of_files:
        with open(f'{folder}/{f}') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                user_ans.append([row[val] for val in [0,1,2,4,5,6]])
                break
    return user_ans

# Answer comparison page
def answer_page(title="Compare your answers"):
   with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    gr.Markdown(f"Please click the below `Compare' button to compare your answers against the correct ones.")
    load_btn = gr.Button("Compare")
    OUTPUT = gr.Markdown()
    @load_btn.click(outputs=[OUTPUT])
    def btn_click():
        answer_list = load_answers()
        if debug:
            ans_noAI = ans_AIvid = ans_AItext = ans_AIimage = answer_list[0]
        else:
            ans_noAI = answer_list[0]
            ans_AIvid = answer_list[1]
            ans_AItext = answer_list[2]
            ans_AIimage = answer_list[3]
        out = f"""
            ## Answers: No AI support
                        
            |   Question    |   Correct Answer |     Your Answer     |
            |:-------------:|:----------------:|:----------------------:|
            |Red Backpack|1|{ans_noAI[0]}|
            |Fire Extinguisher| 2|{ans_noAI[1]}|
            |Green high-vis jackets (not worn by a person/dummy)|0|{ans_noAI[2]}|
            |At the first three-way junction, which direction does the robot ahead of you go through?|Left|{ans_noAI[3]}|
            |Do you encounter a path blocked by rocks?|  No|{ans_noAI[4]}|
            |Do you climb any stairs during the run?| Yes - unsuccessfully|{ans_noAI[5]}|    
       
            ## Answers: AI supported Video Output
                        
            |   Question    |   Correct Answer |     Your Answer     |
            |:-------------:|:----------------:|:----------------------:|
            |   Blue Barrel |        2|{ans_AIvid[0]}|
            |Dummy (not a real person) wearing a green high-vis jacket| 0|{ans_AIvid[1]}|
            |White Helmet|1|{ans_AIvid[2]}|
            |Who enters the tunnel before you?|No one|{ans_AIvid[3]}|
            |Do you climb any stairs during the run?|  Yes - successfully |{ans_AIvid[4]}|
            |Do you knock down a door while trying to pass through it?| No|{ans_AIvid[5]}|    
   
            ## Answers: AI supported Text Output
                        
            |   Question    |   Correct Answer |     Your Answer     |
            |:-------------:|:----------------:|:----------------------:|
            |   Blue Rope Bundle |        0|{ans_AItext[0]}|
            |Fire Extinguisher| >2|{ans_AItext[1]}|
            |Drill|2|{ans_AItext[2]}|
            |In the first three-way junction you get inside the tunnel, which direction do you choose to explore?|Middle|{ans_AItext[3]}|
            |Do you encounter a path blocked by rocks?|  Yes|{ans_AItext[4]}|
            |Do you climb any stairs during the run?| No|{ans_AItext[5]}|    
 
            ## Answers: AI supported Image Gallery Output
                        
            |   Question    |   Correct Answer |     Your Answer     |
            |:-------------:|:----------------:|:----------------------:|
            |Artificial Bamboo Tree|1|{ans_AIimage[0]}|
            |White Helmet| 0|{ans_AIimage[1]}|
            |Black Barrel|>2|{ans_AIimage[2]}|
            |Who enters the tunnel before you?|1 spot and 1 ATR|{ans_AIimage[3]}|
            |Do you encounter a path blocked by rocks?|  No|{ans_AIimage[4]}|
            |Do you knock down a door while trying to pass through it?| Yes|{ans_AIimage[5]}|    
            """
        return out
        
    return page

# Thank you page
def final_page(title="Thank you"):
  with gr.Blocks(title=title) as page:
    gr.Markdown(f"# {title}")
    page_indicator()
    gr.Markdown("### Thank you for your time! Please click the below 'Finish' button to end the study.")
    complete_button = gr.Button("Finish")
    @complete_button.click()
    def complete_click(page=page):
        print("trying to exit")
        page.close()
  return page


def flatten_list(lst):
    flat_list = []
    for item in lst:
        if isinstance(item, list):
            flat_list.extend(flatten_list(item))
        else:
            flat_list.append(item)
    return flat_list

if generic:
    main_pages = [raw_vid_page, gen_video_page, gen_text_page, gen_gallery_page]
else:
    main_pages = [raw_vid_page , query_video_page, query_gallery_page, query_text_page]

if debug:
   main_pages = [raw_vid_page]
    
random.shuffle(main_pages) # randomise the order of tasks
main_pages = [page for main_page in main_pages for page in (main_page, partial(usability_page, main_page.__defaults__[0]))]

# arranging the pages
pages = [
    consent_page,
    inst_page,
    familiarity_page,
    *main_pages,
    summary_page,
    answer_page,
    final_page,
]
# pages = pages[:3]  # reduce for testing
N_PAGES = len(pages)
pages = [page() for page in pages]  # make 'em!


for curr_page, next_page in zip(pages[:-1], pages[+1:]):
    with curr_page:
        if curr_page.title == "Research Participant Consent Form":
           gr.Markdown("Once you click the below button, you cannot go back.")
           next_button = gr.Button("I have reviewed the above information and agree to participate in this user study")
        else:
           gr.Markdown("Once you click Next, you cannot go back.")
           next_button = gr.Button("Next")
        jump_text = gr.Textbox(visible=False)

        inputs = []
        get_inputs(curr_page, inputs, main_tab_id=curr_page.title)
        if f"{curr_page.title}: time" not in headers:
            headers.append(f"{curr_page.title}: time")

        @next_button.click(inputs=inputs, outputs=jump_text)
        def go_next_page(*inputs, curr_id=curr_page.title, next_id=next_page.title, headers=headers):
            print(f"go_next_page({curr_id=}, {next_id=})")
            if len(inputs) == 11: #only in the AI ones, this is 11?
                if inputs[-1] == '':
                    inputs = inputs[:-1] + ("Empty",)
            elif len(inputs) == 6: #this is assuming only the finla page has 6 inputs per page
                if inputs[1] == '':
                   inputs = (inputs[0],) + ("Empty",) + inputs[2:]
                if inputs[3] == '':
                   inputs = inputs[:3] + ("Empty",) + inputs[4:]
                if inputs[5] == '':
                   inputs = inputs[:-1] + ("Empty",)

            for i in inputs:
                print(i)
                if not i:
                    if debug:
                       gr.Warning("You must answer all the questions to continue (check disabled).")
                       #time.sleep(1)
                    else:
                       raise gr.Error("You must answer all the questions to continue.")

            # print data somewhere
            if inputs:
                data.append(inputs)
            
            # tab timings
            if curr_id not in start_times:
                print("START TIME WAS MISSED")  # hopefully just the first one
                start_times[curr_id] = beginning
            end_time = time.time()
            times_spent[curr_id] = time_spent = end_time - start_times[curr_id]
            print(f"Time spent on {curr_id}: {time_spent} seconds")
            data.append(times_spent[curr_id])

            with open(f'{folder}/{curr_id}.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(flatten_list(inputs))
                writer.writerow([times_spent[curr_id]])

            start_times[next_id] = time.time()

            print(f"{urls[next_id]=}")
            return urls[next_id]
        
        # next_button.click(go_next_page, inputs=inputs, outputs=jump_text)
        jump_text.change(None, inputs=jump_text, js="(url) => window.location=url")


for demo in pages:
    demo.queue()
    demo.launch(prevent_thread_lock=True)
    urls[demo.title] = demo.local_url


while all(demo.is_running for demo in pages):
    time.sleep(1)

print("DEMO CLOSED")

with open(filename, 'a', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(headers)
    data = flatten_list(data)
    writer.writerow(data)
