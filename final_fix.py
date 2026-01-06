
import os

file_path = r'c:\Users\Martin\Desktop\Asistente Andrea\app\templates\dashboard.html'

def apply_global_fix():
    print(f"Reading {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        print("UTF-8 read failed, trying cp1252")
        with open(file_path, 'r', encoding='cp1252') as f:
            content = f.read()

    # GLOBAL REPLACEMENT of malicious space-in-brace
    # This covers configs object AND legacy variables
    new_content = content.replace('{ {', '{{').replace('} }', '}}')
    
    # Specific check for legacy block to be sure
    if 'activeVoice: {{' not in new_content and 'activeVoice: { {' not in new_content:
        # Maybe it's activeVoice: { {
        pass
        
    print(f"Occurrences of '{{ {{' found: {content.count('{ {')}")
    print(f"Occurrences of '}} }}' found: {content.count('} }')}")
    
    if content == new_content:
        print("No changes needed (content matches).")
    else:
        print("Writing fixed content...")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Write complete.")

if __name__ == "__main__":
    apply_global_fix()
