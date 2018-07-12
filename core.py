
import requests
from Api import AipClient
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont,ImageOps
from fontTools.ttLib import TTFont
import secure
from helper import ImageBytes
from db import RedisClient
from user_agent import generate_user_agent
APP_ID = secure.APP_ID
API_KEY = secure.API_KEY
SECRET_KEY = secure.SECRET_KEY
REDIS_URL = secure.REDIS_URL

class TycTTF():
    _instance = {}

    def __init__(self,font_key,url=None,imgSize=(0,0),imgMode='RGB',bg_color=(0,0,0),fg_color=(255,255,255),fontsize=30):
        self.imgSize = imgSize
        self.imgMode = imgMode
        self.fontsize = fontsize
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.font_key = font_key
        self.url = self.make_url
        self.get_ttl()
        self.client = AipClient(APP_ID, API_KEY, SECRET_KEY,REDIS_URL)
        self.r = RedisClient(REDIS_URL)
    
    def __new__(cls, url, *args, **kw):
        '''
        伪单例模式 缓存优化
        '''
        if url not in cls._instance:
            cls._instance[url] = super().__new__(cls)
        return cls._instance[url]

    @property
    def make_url(self):
        if self.font_key.__len__() == 8:
            return 'https://static.tianyancha.com/fonts-styles/fonts/%s/%s/tyc-num.woff' % (self.font_key[:2], self.font_key)
        else:
            return 'https:' + self.font_key

    def get_ttl(self):
        res = requests.get(self.url, headers={'User-Agent':generate_user_agent(os=('win',))},timeout=10)
        # PIL 字体对象
        self.font = ImageFont.truetype(BytesIO(res.content),self.fontsize)
        # ttf字体对象
        self.ttf = TTFont(BytesIO(res.content))
        # 反向解析 获取字体库所有文字 
        self.strings = {hex(string).replace('0x','\\u').encode('utf-8').decode('unicode-escape') if string > 2**8 else hex(string).replace('0x','\\x').encode('utf-8').decode('unicode-escape') for string in self.ttf.getBestCmap().keys() }

    def GenLetterImage(self,letters:str):
        self.letters = letters
        (self.letterWidth,self.letterHeight) = self.font.getsize(letters)
        if self.imgSize==(0,0):
            # 文字大小基础上 长宽各加10个像素点
            self.imgSize=(self.letterWidth+10,self.letterHeight+10)
        self.imgWidth,self.imgHeight=self.imgSize
        # new一个image对象  
        self.img = Image.new(self.imgMode, self.imgSize, self.bg_color)
        # 画笔对象
        self.drawBrush = ImageDraw.Draw(self.img)
        textY0 = (self.imgHeight-self.letterHeight+1)/2
        textY0 = int(textY0)
        textX0 = int((self.imgWidth-self.letterWidth+1)/2)
        # 从font对象内获取 letter 映射 文字  并写入空白image对象内
        self.drawBrush.text((textX0,textY0), self.letters, fill=self.fg_color,font=self.font)

    def _orc(self, word:str):
        # image = pretreat_image(self.img)
        self.GenLetterImage(word)
        # 实例化image容器
        img = ImageBytes()
        # 将img bytes 传给image容器
        self.img.save(img, 'JPEG')
        if word in {'0','1','2','3','4','5','6','7','8','9','x'}:
            # 数字 用eng 解析
            kwarg = {'language_type':'ENG'}
        else:
            # 其他使用中英文
            kwarg = {'language_type':'CHN_ENG'}
        return self.client.run(img.img,self.font_key,word,**kwarg)

    def orc(self,word:str):
        if self.r.hexists(self.url, word):
            return self.r.hget(self.font_key, word).decode('utf-8')
        else:
            return self._orc(word)

    def run(self, word:str):
        string = ''
        for letter in word:
            if letter in self.strings:
                string += self.orc(letter)
            else:
                string += letter
        return string