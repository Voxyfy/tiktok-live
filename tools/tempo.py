# Şarkının tempo haritası: her 20 sn'lik dilimde baskın vuruş hızı (100-170 BPM arası).
#   python3 -I tools/tempo.py public/audio/horon.mp3 > public/audio/horon-tempo.json
# Sahne bu haritayla dans vuruşunu müziğin o anki temposuna eşler.
import sys, subprocess, array, json
src = sys.argv[1]; sr = 11025; hop = sr // 100; win = 20
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout)
out = []
for start in range(0, int(dur) - 5, win):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(start), '-t', str(win), '-i', src, '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'], capture_output=True).stdout
    a = array.array('h'); a.frombytes(raw[:len(raw) // 2 * 2])
    env = [sum(abs(x) for x in a[i:i + hop]) / hop for i in range(0, len(a) - hop, hop)]
    on = [max(0, env[i] - env[i - 1]) for i in range(1, len(env))]
    if len(on) < 200: continue
    m = sum(on) / len(on); on = [x - m for x in on]
    score = {lag: sum(on[i] * on[i + lag] for i in range(len(on) - lag)) for lag in range(30, 61)}   # 100-200 BPM (horon halaydan hızlı)
    lag = max(score, key=score.get)
    out.append([start + win / 2, round(6000 / lag, 1)])
    print(start, out[-1][1], file=sys.stderr)
json.dump(out, sys.stdout)
