import os
import subprocess

def run_cmd(cmd):
    subprocess.check_call(cmd, shell=True)

# We already successfully used tree-filter previously which rewrote all commits!
# Let's verify if git log -p still has any IP.
print('Sanitization script ready')
