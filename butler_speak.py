import sys
import re
import subprocess

def clean_markdown(text):
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '[Code block omitted]', text)
    # Remove inline code formatting
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Convert markdown links to just the link text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove images
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    # Remove bold/italic markers
    text = re.sub(r'\*\*([^*]+)\*\*|__([^_]+)__', r'\1\2', text)
    text = re.sub(r'\*([^*]+)\*|_([^_]+)_', r'\1\2', text)
    # Remove headings symbols
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Remove bullet points symbols
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    return text.strip()

if __name__ == '__main__':
    raw_text = sys.argv[1] if len(sys.argv) > 1 else "No text provided."
    cleaned = clean_markdown(raw_text)
    if not cleaned:
        cleaned = "Nothing to speak."
    
    python_bin = "/home/pndhpndh/miniconda3/envs/avatar/bin/python3"
    tts_script = "/home/pndhpndh/assistant/tts.py"
    
    print(f"Butler clean speaking: {cleaned}")
    subprocess.run([python_bin, tts_script, cleaned])
