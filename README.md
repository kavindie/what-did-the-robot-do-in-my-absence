# ‘What did the Robot do in my Absence?’ <br> Video Foundation Models to Enhance Intermittent Supervision

[Project webpage](https://kavindie.github.io/what-did-the-robot-do-in-my-absence/)

# Set-up guide

### Download the git repository
```console
$ cd <place you want to create the project>
$ git clone https://github.com/kavindie/what-did-the-robot-do-in-my-absence.git
```
       
### Clone the  relevant git repositories into your working folder
1. [Languagebind](https://github.com/PKU-YuanGroup/LanguageBind)
2. [Ask-Anything](https://github.com/OpenGVLab/Ask-Anything) : videochat2 can be found inside
   

```console
$ git submodule update --init LanguageBind/
$ git submodule update --init Ask-Anything/
$ mkdir vids # The folder with long videos you want to queries from
$ # Create simlinks
$ ln -s Ask-Anything/video_chat2 .
$ ln -s LanguageBine/langugaebind .
$ ln -s video_chat2/conversation.py .
$ ln -s <path to checkpoints>/*.pth . # Alternatively you can download the checkpoints straight into the repo (see below)
```

### Download relevant checkpoints

   * [UMT_l16.pth](https://pjlab-gvm-data.oss-cn-shanghai.aliyuncs.com/videochat2/umt_l16_qformer.pth)
   * [videochat2_7b_stage2.pth](https://huggingface.co/OpenGVLab/videochat/resolve/main/videochat2_7b_stage2.pth)
   * [videochat2_7b_stage3.pth](https://huggingface.co/OpenGVLab/videochat/resolve/main/videochat2_7b_stage3.pth)
   * [vicuna-7b-v0](https://github.com/OpenGVLab/Ask-Anything/tree/main/video_chat#running-usage)
     * [Llama](https://huggingface.co/huggyllama/llama-7b/tree/main)
     * [Vicuna](https://huggingface.co/lmsys/vicuna-7b-delta-v0/tree/main)
       * Make sure the fastchat version is <=0.1.10.
       * Note: Instead of Vicuna, you can download checkpoints related to Mistral, make sure the config and run files are changed as stated by the authors.


### Create a virtual environment
Note: Python 3.12.0 is the version being used.
```console
$ python3 -m venv .venv
$ . .venv/bin/activate
$ pip install -r requirements.txt
$ pip install seaborn itables statsmodels moviepy gradio nltk wordcloud
```

### Run the analysis
To run the analysis simply run the analysis.ipynb

### Run the study interface
Run the interface.py script for this
