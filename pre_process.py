# This script will pre-process the video and save accordingly
# Import packages
from moviepy.editor import VideoFileClip, concatenate_videoclips
import tqdm 
import os
from pathlib import Path
import fnmatch
import re
from PIL import Image
import time

# Let's focus on one video at a time

def process_video(video_path, fps_required):
    clip = VideoFileClip(video_path)
    fps_clip = clip.fps
    fps_required = min(fps_required, fps_clip)

    output_dir = os.path.join(Path(video_path).parent.absolute(), Path(video_path).name.split('.')[0], f"fps_{fps_required}")
    output_dir_frames = os.path.join(output_dir, 'frames') #frames are saved in a folder called frames in the output_dir
    output_dir_mini_videos = os.path.join(output_dir, 'mini_videos') #video segemnts are saved in a folder called mini_videos in the output_dir
    mini_video_files = []
    images = []

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        os.makedirs(output_dir_mini_videos)
        os.makedirs(output_dir_frames)
    else:
        # This is making sure that the video was processed without interrupts. If so vid_details.txt should exist
        if os.path.exists(f'{output_dir}/vid_details.txt'):
            # read the mini_video file names and frame file names into a list and sort it
            for file in os.listdir(output_dir_mini_videos):
                if fnmatch.fnmatch(file, 'mini_video*.mp4'):
                    mini_video_files.append(os.path.join(output_dir_mini_videos, file))
            for file in os.listdir(output_dir_frames):
                if fnmatch.fnmatch(file, 'frame*.jpg'):
                    images.append(os.path.join(output_dir_frames, file))

            mini_video_files.sort(key=lambda x: int(re.findall(r'\d+', x.split('/')[-1])[0]))
            images.sort(key=lambda x: int(re.findall(r'\d+', x.split('/')[-1])[0]))

            return mini_video_files, images, output_dir
        else:
            # can be taken out of the if else block too. 
            print(f"Pre-processing the video segments")
            num_secs = 8//fps_required # because langugaebind requires 8 frames per vid segment
            # Iterate over the video in 8-second intervals

            if num_secs == 0:
                num_secs = num_secs = 8/fps_required
                start_time = 0
                end_time = 0 + num_secs
                keep_adding = True
                i = 0
                while keep_adding:
                    mini_video = clip.subclip(start_time, end_time)
                    mini_video = mini_video.set_fps(fps_required)
                    file_name = f"{output_dir_mini_videos}/mini_video_{i}.mp4"
                    mini_video.write_videofile(file_name, fps=fps_required)
                    mini_video_files.append(file_name)

                    start_time = end_time
                    if start_time >=  clip.duration:
                        keep_adding = False
                    else:
                        end_time =  min(start_time + num_secs, clip.duration)
                    i += 1

            else:
                for i in range(0, int(clip.duration), num_secs):
                    start_time = i
                    end_time = min(i + num_secs, clip.duration)
                    mini_video = clip.subclip(start_time, end_time)
                    mini_video = mini_video.set_duration(num_secs).set_fps(fps_required)

                    # Define the file name for the mini video
                    file_name = f"{output_dir_mini_videos}/mini_video_{i//num_secs}.mp4"

                    # Write the mini video to a file
                    mini_video.write_videofile(file_name, fps=1)

                    # Append the file name to the list
                    mini_video_files.append(file_name)
            

            # print(f"Pre-processing the image frames")
            frames = clip.iter_frames(fps=fps_required)
            for i, f in tqdm.tqdm(enumerate(frames)):
                file_name = f"{output_dir_frames}/frame_{i}.jpg"
                Image.fromarray(f).save(file_name)
                images.append(file_name)
            
            print(f"I have {len(mini_video_files)} video segments.")
            print(f"I have {len(images)} frames.")

            with open (f'{output_dir}/vid_details.txt', 'w') as file:
                # does not matter what you write as long as this file exists at the end 
                file.write(f'{output_dir_mini_videos}, mini_video_{len(mini_video_files)-1}.mp4\n{output_dir_frames}, frame_{len(images)-1}.jpg')

            return mini_video_files, images, output_dir

def combine_videos(video_files, output_file):
    video_clips = [VideoFileClip(file) for file in video_files]
    
    # Concatenate video clips
    final_clip = concatenate_videoclips(video_clips)
    
    # Write the final concatenated clip to a file
    final_clip.write_videofile(output_file)
    
    # Close the clips
    final_clip.close()
    for clip in video_clips:
        clip.close()

def convert_to_hms(seconds):
    # convert seconds to minutes and seconds
    return time.strftime('%M:%S', time.gmtime(seconds))

