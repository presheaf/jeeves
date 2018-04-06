import subprocess

while True:
    completed = subprocess.run(['python', 'jeeves.py'])
    if completed.returncode == 65:
        print("Jeeves turned off. Aborting")
        break
    print("Jeeves stopped working! Restarting")
    
