#http://stackoverflow.com/questions/26289679/python-create-image-with-multiple-colors-and-add-text
import PIL
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw
import textwrap
import os
import uuid
import subprocess


dir_path = os.path.dirname(os.path.realpath(__file__))

def get_spoiler_gif(text):
    wrapped = textwrap.wrap(text, 55)
    font = ImageFont.truetype(dir_path + "/aileron_font/Aileron-SemiBold.otf", 13)

    img_cover = Image.new("RGBA", (400, (20 * len(wrapped)) + 20), (64, 64, 64))
    draw_cover = ImageDraw.Draw(img_cover)
    draw_cover.text((10, 10), "( Hover to reveal spoiler )", (160, 160, 160), font=font)

    img_spoiler = Image.new("RGBA", (400, (20 * len(wrapped)) + 20), (64, 64, 64))
    draw_spoiler = ImageDraw.Draw(img_spoiler)
    for i, line in enumerate(wrapped):
        draw_spoiler.text((10, (20 * i) + 10), line, (160, 160, 160), font=font)

    unique = str(uuid.uuid4())
    file_cover = "gif_tmp/img_cover_{}.png".format(unique)
    file_spoiler = "gif_tmp/img_spoiler_{}.png".format(unique)
    file_gif = "gif_tmp/{}.gif".format(unique)

    img_cover.save(file_cover)
    img_spoiler.save(file_spoiler)

    cmd = "convert -delay 2 -loop 1 {} {} {}".format(file_cover, file_spoiler, file_gif)
    process = subprocess.Popen(cmd.split())
    process.wait()

    os.remove(file_cover)
    os.remove(file_spoiler)
    #os.remove(file_gif)

get_spoiler_gif("abcdefghijklmnopqrstuvwxyz abcdefghijklmnopqrstuvwxyz abcdefghijklmnopqrstuvwxyz")

# convert -delay 2 -loop 0 img_cover.png img_spoiler.png test.gif
#ImageMagick
