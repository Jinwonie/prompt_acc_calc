########## Import ##########
import cv2
import base64
import sqlite3
import numpy as np
import pandas as pd
from PIL import Image
from io import BytesIO
import skimage.metrics as metrics

########## Functions ##########
def img_resizing(org_img_dir, target_img_dir):
    org_img = Image.open(org_img_dir)
    target_img = Image.open(target_img_dir)
    
    org_img_size = org_img.size
    target_img_size = target_img.size
    
    if org_img_size != target_img_size:
        target_img = target_img.resize((org_img_size[0], org_img_size[1]), Image.Resampling.LANCZOS)
    
    return target_img

def image_accuracy_calculator(org_img_dir, target_img_dir):    
    org_img = cv2.imread(org_img_dir)
    target_np_img = np.array(img_resizing(org_img_dir, target_img_dir))
    target_img = cv2.cvtColor(target_np_img, cv2.COLOR_RGB2BGR)
    
    gs_org_img = cv2.cvtColor(org_img, cv2.COLOR_BGR2GRAY)
    gs_target_img = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
    
    acc = round(metrics.structural_similarity(gs_org_img, gs_target_img) * 100, 2)
    
    return acc

def load_df(sql_dir, sql_query):
    conn = sqlite3.connect(sql_dir)
    df = pd.read_sql(sql_query, conn)
    df = df.loc[df.groupby(["usr_nm", "phone_num"])["acc"].idxmax(), ["usr_nm", "acc", "img_data"]]
    df = df.sort_values(by="acc", ascending=False).reset_index(drop=True)
    df = df.head(10)
    conn.close()
    
    return df

def image_formatter(img_binary):
    if img_binary:
        image = Image.open(BytesIO(img_binary))  # 바이너리 데이터를 PIL 이미지로 변환
        img_buffer = BytesIO()
        image.save(img_buffer, format="PNG")  # 이미지를 PNG로 변환 후 저장
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()  # Base64로 변환 후 디코딩

        return f'<img src="data:image/png;base64,{img_base64}" width="100">'

    return "No Image"
