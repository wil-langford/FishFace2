from celery import Celery
import os
import os.path as os_path

from PIL import Image

with open(os_path.join(os.environ['HOME'], 'var', 'run', 'redis.hostname'), 'rt') as f:
    hostname = f.read().strip()

redis_url = 'redis://{}'.format(hostname)

app = Celery('tasks', backend=redis_url, broker=redis_url)

@app.task
def write_file_by_name(filename):
    full_path = os_path.join('/home/wsl/test_out',filename) 
    with open(full_path, 'wt') as f:
        f.write("I'm a good worker and I'm writing to filename {}!\n".format(filename))

    return full_path

@app.task
def add(x, y):
    return x + y

@app.task
def tsum(numbers):
    return sum(numbers)

@app.task
def normalize_jpeg_file(jpeg_filename):
    image = Image.open(jpeg_filename)
    image.convert('L')
    return image.mode