import os
import zipfile

def zip_dir(dir_path, zip_path):
    # Files/directories to ignore
    ignores = {
        'node_modules', '.git', '.venv', 'venv', '__pycache__', 
        '.pytest_cache', 'codebase.zip', 'tech_news_codebase.zip', 
        '.next', 'backend_logs.txt', 'dist', 'build'
    }
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dir_path):
            # Modify dirs in-place to prune ignored directories
            dirs[:] = [d for d in dirs if d not in ignores]
            
            for file in files:
                if file in ignores or file.endswith('.zip') or file.endswith('.log') or file == 'backend_logs.txt':
                    continue
                
                # Create the full path and relative path
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, dir_path)
                
                # Add to zip
                zipf.write(file_path, rel_path)

if __name__ == '__main__':
    src = r'c:\Users\HP\Downloads\tech_news'
    dst = r'c:\Users\HP\Downloads\tech_news\tech_news_codebase.zip'
    print(f"Zipping {src} to {dst}...")
    zip_dir(src, dst)
    print(f"Successfully created {dst}")
