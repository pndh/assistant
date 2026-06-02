import os
import sys
import torch
import sounddevice as sd
import warnings
from flask import Flask, request

# Silence PyTorch logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings("ignore")

# Force path
UMA_DIR = "/home/pndhpndh/assistant/uma_vits"
sys.path.append(UMA_DIR)

import commons
import utils
import ONNXVITS_infer
from text import text_to_sequence

print("Booting Anime Voice Engine...")
config_path = f"{UMA_DIR}/configs/uma_trilingual.json"
onnx_dir = f"{UMA_DIR}/ONNX_net/G_trilingual/"
hps = utils.get_hparams_from_file(config_path)

# Load the heavy model into memory ONCE
net_g = ONNXVITS_infer.SynthesizerTrn(
    len(hps.symbols),
    hps.data.filter_length // 2 + 1,
    hps.train.segment_size // hps.data.hop_length,
    n_speakers=hps.data.n_speakers,
    ONNX_dir=onnx_dir,
    **hps.model
)
_ = net_g.eval()
print("Engine Online! Listening on port 5050...")

app = Flask(__name__)

@app.route('/speak', methods=['POST'])
def speak():
    data = request.json
    raw_text = data.get("text", "Hmph.")

    try:
        # Convert text to sequence IDs
        text_norm = text_to_sequence(raw_text, hps.symbols, hps.data.text_cleaners)
        if hps.data.add_blank:
            text_norm = commons.intersperse(text_norm, 0)

        stn_tst = torch.LongTensor(text_norm)
        x_tst = stn_tst.unsqueeze(0)
        x_tst_lengths = torch.LongTensor([stn_tst.size(0)])

        # 19 = Special Week voice. Change this number for different characters!
        sid = torch.LongTensor([19])

        with torch.no_grad():
            audio_data = net_g.infer(
                x_tst, x_tst_lengths, sid=sid, noise_scale=0.667, noise_scale_w=0.8, length_scale=1.0
            )[0][0, 0].data.cpu().float().numpy()

        # Create flag for avatar lip-sync
        flag_file = "/tmp/avatar_speaking"
        with open(flag_file, 'w') as f:
            f.write("1")

        # Play audio
        sd.play(audio_data, hps.data.sampling_rate)
        sd.wait()

        # Remove flag
        if os.path.exists(flag_file):
            os.remove(flag_file)

        return {"status": "success"}

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

if __name__ == '__main__':
    # Silence the Flask network logs
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(port=5050)
