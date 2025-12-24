"""
curl -X POST http://192.168.50.60:42004/call/transcribe_file -s -H "Content-Type: application/json" -d '{
  "data": [
    [handle_file('http://192.168.50.60:42004/gradio_api/file=G:\\pinokio\\api\\whisper-webui.git\\cache\\GRADIO_TEMP_DIR\\23cb747d6d147f62a9504b7c393c80074856c2afb0f91039ed849d0027e83050\\ElevenLabs_2023-07-30T20_05_31.000Z_Bella_ZDGGhJZc1Bg19hStVLjp.mp3')],
    "",
    false,
    "txt",
    true,
    "small.en",
    "Automatic Detection",
    false,
    5,
    -1,
    0.6,
    "float16",
    5,
    1,
    true,
    0.5,
    "",
    0,
    2.4,
    1,
    1,
    0,
    "",
    true,
    "[-1]",
    1,
    false,
    ""'“¿([{-",
    ""'.。,，!！?？:：”)]}、",
    0,
    30,
    0,
    "",
    0.5,
    1,
    24,
    false,
    0.5,
    250,
    9999,
    1000,
    2000,
    false,
    "cuda",
    "",
    false,
    "UVR-MDX-NET-Inst_HQ_4",
    "cuda",
    256,
    false,
    true
]}' \
  | awk -F'"' '{ print $4}' \
  | read EVENT_ID; curl -N http://192.168.50.60:42004/call/transcribe_file/$EVENT_ID
"""
# from gradio_client import Client, file

# client = Client("http://192.168.50.60:42004/")
import json
import requests
from pprint import pprint as pp
import time

from pathlib import Path

def dprint(*a, **kw):
    pass

def handle_file(filepath_or_url):
    s = str(filepath_or_url)
    data = {"path": s, "meta": {"_type": "gradio.FileData"}}
    # if is_http_url_like(s):
    return {**data, "orig_name": s.split("/")[-1], "url": s}
    # elif Path(s).exists():
    #     return {**data, "orig_name": Path(s).name}
    # else:
    #     raise ValueError(
    #         f"File {s} does not exist on local filesystem and is not a valid URL."
    #     )


def is_http_url_like(possible_url) -> bool:
    """
    Check if the given value is a string that looks like an HTTP(S) URL.
    """
    if not isinstance(possible_url, str):
        return False
    return possible_url.startswith(("http://", "https://"))


fp = 'G:\\pinokio\\api\\whisper-webui.git\\cache\\GRADIO_TEMP_DIR\\c768b8fb0b2fdf10980c0e60bebb0bbe0ba816b62f808a4326f534de6ac47704\\ElevenLabs_2023-07-30T20_07_34.000Z_premade_Charlotte.mp3'
fp = 'G:\\pinokio\\api\\whisper-webui.git\\cache\\GRADIO_TEMP_DIR\\mia.wav'

f = {
    "path": f"{fp}",
    "url": f"http://192.168.50.60:42004/gradio_api/file={fp}",
    "orig_name": "mia.wav",
    # "orig_name": "ElevenLabs_2023-07-30T20_07_34.000Z_premade_Charlotte.mp3",
    # "size": 213995,
    # "mime_type": "audio/mpeg",
    "meta": {
        "_type": "gradio.FileData"
    }
}

dprint(f)
d = dict(
   files=[f],
  input_folder_path="",
  include_subdirectory=False,
  file_format="txt",
  add_timestamp=True,
  progress="small.en",
  param_6="Automatic Detection",
  param_7=False,
  param_8=5,
  param_9=-1,
  param_10=0.6,
  param_11="float16",
  param_12=5,
  param_13=1,
  param_14=True,
  param_15=0.5,
  param_16="",
  param_17=0,
  param_18=2.4,
  param_19=1,
  param_20=1,
  param_21=0,
  param_22="",
  param_23=True,
  param_24="[-1]",
  param_25=1,
  param_26=False,
  param_27="\"'“¿([{-",
  param_28="\"'.。,，!！?？:：”)]}、",
  param_29=0,
  param_30=30,
  param_31=0,
  param_32="",
  param_33=0.5,
  param_34=1,
  param_35=24,
  param_36=False,
  param_37=0.5,
  param_38=250,
  param_39=9999,
  param_40=1000,
  param_41=2000,
  param_42=False,
  param_43="cuda",
  param_44="",
  param_45=False,
  param_46="UVR-MDX-NET-Inst_HQ_4",
  param_47="cuda",
  param_48=256,
  param_49=False,
  param_50=True,
  # api_name="/transcribe_file"
)


url = "http://192.168.50.60:42004/gradio_api/call/transcribe_file"
headers = {
    'Content-Type': "application/json",
    'Accept': "*/*",
    # "Authorization":f"Bearer {AGENT_ACCESS_KEY}",
    'Cache-Control': "no-cache",
}
data = {
        "data": list(d.values())
    }
data = json.dumps(data)

dprint('=========')
dprint(url)

response = requests.request("POST", url, data=data, headers=headers)
content = response.json()
pp(content)
dprint('=========')

"""

good:
    {'event_id': 'f18b627edf8d48b4813b322fcd354c3f'}

bad:

    http://192.168.50.60:42004/gradio_api/call/generate_unified_tts
    {'detail': [{'input': ['text_input',
                           'tts_engine',
                           'audio_format',
                           'chatterbox_ref_audio',
                           'chatterbox_exaggeration',
                           'chatterbox_temperature',
                           'chatterbox_cfg_weight',
                           'chatterbox_chunk_size',
                           'chatterbox_seed',
                           'chatterbox_mtl_ref_audio',
                           'chatterbox_mtl_language',
                           'chatterbox_mtl_exaggeration',
                           'chatterbox_mtl_temperature',
                           'chatterbox_mtl_cfg_weight',
                           'chatterbox_mtl_repetition_penalty',
                           'chatterbox_mtl_min_p',
                           'chatterbox_mtl_top_p',
                           'chatterbox_mtl_chunk_size',
                           'chatterbox_mtl_seed',
                           'kokoro_voice',
                           'kokoro_speed',
                           'fish_ref_audio',
                           'fish_ref_text',
                           'fish_temperature',
                           'fish_top_p',
                           'fish_repetition_penalty',
                           'fish_max_tokens',
                           'fish_seed',
                           'indextts_ref_audio',
                           'indextts_temperature',
                           'indextts_seed',
                           'indextts2_ref_audio',
                           'indextts2_emotion_mode',
                           'indextts2_emotion_audio',
                           'indextts2_emotion_description',
                           'indextts2_emo_alpha',
                           'indextts2_happy',
                           'indextts2_angry',
                           'indextts2_sad',
                           'indextts2_afraid',
                           'indextts2_disgusted',
                           'indextts2_melancholic',
                           'indextts2_surprised',
                           'indextts2_calm',
                           'indextts2_temperature',
                           'indextts2_top_p',
                           'indextts2_top_k',
                           'indextts2_repetition_penalty',
                           'indextts2_max_mel_tokens',
                           'indextts2_seed',
                           'indextts2_use_random',
                           'f5_ref_audio',
                           'f5_ref_text',
                           'f5_speed',
                           'f5_cross_fade',
                           'f5_remove_silence',
                           'f5_seed',
                           'higgs_ref_audio',
                           'higgs_ref_text',
                           'higgs_voice_preset',
                           'higgs_system_prompt',
                           'higgs_temperature',
                           'higgs_top_p',
                           'higgs_top_k',
                           'higgs_max_tokens',
                           'higgs_ras_win_len',
                           'higgs_ras_win_max_num_repeat',
                           'kitten_voice',
                           'voxcpm_ref_audio',
                           'voxcpm_ref_text',
                           'voxcpm_cfg_value',
                           'voxcpm_inference_timesteps',
                           'voxcpm_normalize',
                           'voxcpm_denoise',
                           'voxcpm_retry_badcase',
                           'voxcpm_retry_badcase_max_times',
                           'voxcpm_retry_badcase_ratio_threshold',
                           'voxcpm_seed',
                           'gain_db',
                           'enable_eq',
                           'eq_bass',
                           'eq_mid',
                           'eq_treble',
                           'enable_reverb',
                           'reverb_room',
                           'reverb_damping',
                           'reverb_wet',
                           'enable_echo',
                           'echo_delay',
                           'echo_decay',
                           'enable_pitch',
                           'pitch_semitones'],
                 'loc': ['body'],
                 'msg': 'Input should be a valid dictionary or object to extract '
                        'fields from',
             'type': 'model_attributes_type'}]}
"""

eid = content['event_id']
eurl = f'{url}/{eid}'
dprint(url)
response = requests.request("GET", eurl, headers=headers)
content = response.text
# dprint(content)

dprint('=========')

r = []
for line in content.split('\n'):
    ss = 'data: '
    if line.startswith(ss):
        r.append(line[len(ss):])
        continue
    ss = 'event: '
    if line.startswith(ss):
        dprint('# ..', line)

dprint('=========')

dprint(r)
dprint('=========')

def download_file(url):
    local_filename = url.split('/')[-1].split('\\')[-1]
    # NOTE the stream=True parameter below
    time.sleep(1)

    with requests.get(url, stream=False) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                #if chunk:
                f.write(chunk)
    return local_filename


for line in r:
    try:

        text, data = json.loads(line)
        dprint(f"\nTEXT:\n\n{text}\n")
        dprint(f"\nDATA:\n")

        """
        an entity looks like this:
        {'is_stream': False,
             'meta': {'_type': 'gradio.FileData'},
             'mime_type': None,
             'orig_name': 'mia-1223022826.txt',
             'path': 'G:\\pinokio\\api\\whisper-webui.git\\cache\\GRADIO_TEMP_DIR\\64d1c755a088f5396b0b1f16a1b7d38924608442a6b8463a01498895f07c1388\\mia-1223022826.txt',
             'size': 165,
             'url': 'http://192.168.50.60:42004/gradio_ap/gradio_api/file=G:\\pinokio\\api\\whisper-webui.git\\cache\\GRADIO_TEMP_DIR\\64d1c755a088f5396b0b1f16a1b7d38924608442a6b8463a01498895f07c1388\\mia-1223022826.txt'}

        """
        for entity in data:
            # pp(entity)
            if entity.get('meta', {}).get('_type', None) == 'gradio.FileData':
                dprint('Got file data')
                # note the entity['url'] is broken
                #
                name = download_file(f"http://192.168.50.60:42004/gradio_api/file={entity['path']}")
                print('\n===========\n\n', Path(name).read_text())
        # for item in items:
        #     print(' - ', item)
    except json.decoder.JSONDecodeError:
        print('- A decode error - ')
        print(line)
    print('\n---\n')

