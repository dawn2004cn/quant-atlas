import psutil

def list_python_processes():
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        if proc.info['name'].lower().startswith('python'):
            print(f"PID: {proc.info['pid']}, Name: {proc.info['name']}, Path: {proc.info['exe']}")

if __name__ == "__main__":
    list_python_processes()