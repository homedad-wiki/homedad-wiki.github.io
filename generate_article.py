#!/usr/bin/env python3
"""
動物部落格文章自動生成腳本
- 使用 LLM 生成科普文章
- 封面使用 Wikipedia 圖片
- 內文使用 Pexels 圖片
"""

import csv
import random
import datetime
import requests
from pathlib import Path

# 設定路徑
BLOG_DIR = Path("/home/vanix/.openclaw/workspace/blog-temp")
ANIMALS_CSV = Path("/home/vanix/.openclaw/workspace/animals_500.csv")
COUNTER_FILE = Path("/tmp/animal-scripts/.counter")
ASSETS_DIR = BLOG_DIR / "assets" / "images"

# 動物數據
ANIMALS = []
WIKIPEDIA_HEADERS = {'User-Agent': 'OpenClaw-Blog/1.0 (Animal Wiki; https://github.com/homedad-wiki)'}
# Pexels API Key
PEXELS_API_KEY = "LO13kSPnwxvcNreuuEL8MLNudLXOs6pI2TL71vG9C3uehJwtKD9V6tCA"

import os

# GitHub Token（從環境變數讀取）
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not GITHUB_TOKEN:
    print("⚠️ GITHUB_TOKEN 環境變數未設定，無法推送")

# LLM 模型（使用 cloud 模型）
OLLAMA_MODEL = "minimax-m2.5:cloud"

def load_animals():
    """載入動物清單"""
    global ANIMALS
    with open(ANIMALS_CSV, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('|')
            if len(parts) >= 3:
                ANIMALS.append({
                    'slug': parts[0].strip(),
                    'name': parts[1].strip(),
                    'location': parts[2].strip()
                })
    print(f"載入 {len(ANIMALS)} 種動物")

def get_next_animal():
    """取得下一個要處理的動物"""
    counter = 0
    if COUNTER_FILE.exists():
        with open(COUNTER_FILE, 'r') as f:
            counter = int(f.read().strip())
    
    animal = ANIMALS[counter % len(ANIMALS)]
    
    counter += 1
    COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(COUNTER_FILE, 'w') as f:
        f.write(str(counter))
    
    return animal

def get_wikipedia_image(animal_name):
    """從 Wikipedia 取得單張封面圖片"""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{animal_name}"
    try:
        resp = requests.get(url, timeout=10, headers=WIKIPEDIA_HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            if "originalimage" in data:
                return data["originalimage"]["source"]
            if "thumbnail" in data:
                return data["thumbnail"]["source"]
    except Exception as e:
        print(f"Wikipedia API 錯誤: {e}")
    return None

def get_pexels_images(animal_name, num_images=5):
    """從 Pexels 取得多張內文圖片"""
    if not PEXELS_API_KEY:
        print(f"⚠️ PEXELS_API_KEY 未設定，跳過圖片")
        return []
    
    headers = {"Authorization": PEXELS_API_KEY}
    
    keywords = [
        animal_name.replace("_", " "),
        f"{animal_name.replace('_', ' ')} wildlife",
        animal_name,
    ]
    
    for keyword in keywords:
        try:
            url = f"https://api.pexels.com/v1/search?query={keyword}&per_page={num_images}"
            resp = requests.get(url, headers=headers, timeout=15)
            
            if resp.status_code == 200:
                data = resp.json()
                photos = data.get("photos", [])
                
                if photos:
                    urls = []
                    for p in photos[:num_images]:
                        src = p.get("src", {})
                        img_url = src.get("large") or src.get("medium")
                        if img_url:
                            urls.append(img_url)
                    
                    if urls:
                        print(f"✅ Pexels 找到 {len(urls)} 張圖片 for {animal_name}")
                        return urls
        except Exception as e:
            print(f"Pexels 錯誤: {e}")
    
    print(f"⚠️ Pexels 找不到圖片 for {animal_name}")
    return []

def call_llm(prompt, system_prompt=None):
    """呼叫本地 LLM 生成內容"""
    import sys
    
    if system_prompt is None:
        system_prompt = "你是一個專業的科普作家，擅長寫給國中生閱讀的動物介紹文章。語言生動活潑，內容豐富有趣。請務必使用繁體中文，不要使用簡體字。"
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    
    try:
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=180
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("message", {}).get("content", "").strip()
            print(f"    ✅ LLM 回應 ({len(content)} 字)", file=sys.stderr)
            return content
        else:
            print(f"    ❌ LLM 錯誤: {resp.status_code}", file=sys.stderr)
    except Exception as e:
        print(f"    ❌ LLM 呼叫錯誤: {e}", file=sys.stderr)
    
    return None

def generate_intro(name, location):
    """生成文章引言段落"""
    prompt = f"""請為「{name}」寫一段 200 字左右的引言，介紹這種動物是 {location} 的動物。
請用繁體中文寫作。
要求：
- 語言生動，適合國中生閱讀
- 加入一個有趣的問題來引起讀者興趣
- 不要使用列表或標題符號
"""
    return call_llm(prompt)

def generate_appearance(name, location):
    """生成外觀介紹段落"""
    prompt = f"""請為「{name}」寫一段關於外觀的介紹，約 300 字。
請用繁體中文寫作。
要求：
- 描述{name}的外型特色
- 說明{name}如何適應 {location} 的環境
- 加入一個「你知道嗎？」的有趣小知識
- 不要使用列表
"""
    return call_llm(prompt)

def generate_habitat(name, location):
    """生成棲息地介紹段落"""
    prompt = f"""請為「{name}」寫一段關於棲息地的介紹，約 300 字。
請用繁體中文寫作。
要求：
- 描述{name}主要分布在 {location} 的哪些地方
- 描述這些環境的特色
- 說明{name}為什麼適合生活在這些環境
- 不要使用列表
"""
    return call_llm(prompt)

def generate_diet(name, location):
    """生成食性介紹段落"""
    prompt = f"""請為「{name}」寫一段關於食性的介紹，約 300 字。
請用繁體中文寫作。
要求：
- 說明{name}是草食性、肉食性還是雜食性
- 描述{name}的獵食或覓食方式
- 可以提及{name}最喜歡吃的食物
- 不要使用列表
"""
    return call_llm(prompt)

def generate_social(name, location):
    """生成社交行為段落"""
    prompt = f"""請為「{name}」寫一段關於社交行為和家庭生活的介紹，約 300 字。
請用繁體中文寫作。
要求：
- 說明{name}是獨居還是群居動物
- 描述{name}的家庭結構
- 提及繁殖和幼崽的照顧
- 不要使用列表
"""
    return call_llm(prompt)

def generate_facts(name, location):
    """生成令人驚奇的知識段落"""
    prompt = f"""請提供 4 個關於「{name}」的有趣知識，每個知識用一小段（約 80 字）描述。
請用繁體中文寫作。
要求：
- 每個知識要有標題（用 ### 開頭）
- 內容要新奇有趣，適合國中生閱讀
- 包含{name}的特殊能力、行為或生態知識
"""
    return call_llm(prompt)

def generate_conservation(name, location):
    """生成保育行動段落"""
    prompt = f"""請為「{name}」寫一段關於保育的介紹，約 300 字。
請用繁體中文寫作。
要求：
- 說明{name}面臨的威脅和挑戰
- 建議國中生可以做的保育行動
- 語言正向積極，鼓勵讀者行動
- 不要使用列表
"""
    return call_llm(prompt)

def generate_title(name, location):
    """用 LLM 生成文章標題"""
    prompt = f"""請為「{name}」生成一個吸引人的文章標題。
請用繁體中文寫作。
要求：
- 標題要包含動物名稱「{name}」
- 標題要包含地點「{location}」
- 不要使用任何動物 emoji（如 🦁🐯等）
- 格式：例如「認識{location}的{name}」或「{name}：{location}的奇妙居民」
- 直接輸出標題文字，不要加任何裝飾符號
"""
    result = call_llm(prompt, system_prompt="你是一個標題產生器，擅長生成吸引人的文章標題。直接輸出標題，不要加任何裝飾。請務必使用繁體中文。")
    if result:
        return result.strip().strip('"').strip("'")
    return f"{name}：{location}的奇妙居民"

def generate_full_article(animal):
    """生成完整文章"""
    name = animal['name']
    slug = animal['slug']
    location = animal['location']
    
    print(f"\n📝 正在生成 {name} 的文章...")
    
    # 取得圖片
    print("📷 取得 Wiki 封面圖片...", flush=True)
    wiki_image = get_wikipedia_image(slug)
    if not wiki_image:
        wiki_image = get_wikipedia_image(name)
    print(f"  封面圖片: {wiki_image[:80] if wiki_image else 'None'}...", flush=True)
    
    print("📷 取得 Pexels 內文圖片...", flush=True)
    pexels_images = get_pexels_images(slug, num_images=5)
    
    # 確保有足夠的圖片（如果沒有就用 wiki 圖片或佔位符）
    placeholder = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/020_The_lion_king_Snyggve_in_the_Serengeti_National_Park_Photo_by_Giles_Laurent.jpg/1280px-020_The_lion_king_Snyggve_in_the_Serengeti_National_Park_Photo_by_Giles_Laurent.jpg"
    while len(pexels_images) < 4:
        pexels_images.append(wiki_image or placeholder)
    
    # 生成各段落
    print("  生成引言...")
    intro = generate_intro(name, location) or f"{name}是{location}的一種特別的動物。"
    
    print("  生成外觀...")
    appearance = generate_appearance(name, location) or f"{name}是一種獨特的動物。"
    
    print("  生成棲息地...")
    habitat = generate_habitat(name, location) or f"{name}主要生活在{location}。"
    
    print("  生成食性...")
    diet = generate_diet(name, location) or f"{name}的食物習慣很有趣。"
    
    print("  生成社交行為...")
    social = generate_social(name, location) or f"{name}的社會行為很有趣。"
    
    print("  生成有趣知識...")
    facts = generate_facts(name, location) or "### 知識1\n有一些有趣的事實。"
    
    print("  生成保育行動...")
    conservation = generate_conservation(name, location) or "讓我們一起保護自然環境！"
    
    print("  生成標題...")
    title = generate_title(name, location)
    
    # 組裝文章
    date_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S +0800')
    
    content = f"""---
title: "{title}"
author: 小白
date: {date_str}
categories: [動物介紹]
tags: [{name}, {location}, 動物]
pin: false
image:
  path: {wiki_image}
  alt: {name}
toc: true
comments: true
excerpt: "一起認識{location}的可愛動物——{name}！這篇文章適合國中小學生閱讀。"
permalink: /animals/{slug}/
---

# {title}

![{name}]({wiki_image})

## 引言

{intro}

---

## 🐾 認識{name}

### {name}長什麼樣子？

{appearance}

![{name}特寫]({pexels_images[0]})

---

## 🌍 {name}的家

### 棲息地

{habitat}

![{location}環境]({pexels_images[1]})

---

## 🍖 {name}吃什麼？

### 食性

{diet}

![{name}覓食]({pexels_images[2]})

---

## 👨‍👩‍👧‍👦 {name}的家庭

### 社交行為

{social}

![{name}家庭]({pexels_images[3]})

---

## 🌟 令人驚奇的{name}知識

{facts}

---

## 💪 我們可以如何保護{name}？

{conservation}

---

## 延伸閱讀

如果你喜歡這篇文章，以下資源可以讓你了解更多：
- [Wikipedia - {name}](https://en.wikipedia.org/wiki/{slug})
- [National Geographic Kids - {name}](https://www.natgeokids.com/uk/animal-facts/animals/{slug}-facts/)

---

*喜歡這篇文章嗎？記得訂閱我們的部落格，認識更多可愛的動物朋友！* 🐾
"""
    
    return content

def save_article(animal, content):
    """儲存文章"""
    slug = animal['slug']
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    filename = f"{date}-{slug}.md"
    filepath = BLOG_DIR / "_posts" / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 文章已儲存: {filepath}")
    return filepath

def push_to_github():
    """推送到 GitHub"""
    import subprocess
    
    try:
        # Set remote with token
        subprocess.run(["git", "remote", "set-url", "origin", f"https://{GITHUB_TOKEN}@github.com/homedad-wiki/homedad-wiki.github.io.git"], 
                       cwd=BLOG_DIR, check=True)
        
        # Add, commit, push
        subprocess.run(["git", "add", "_posts/"], cwd=BLOG_DIR, check=True)
        subprocess.run(["git", "commit", "-m", "Add new animal article"], cwd=BLOG_DIR, check=True)
        result = subprocess.run(["git", "push", "origin", "main"], cwd=BLOG_DIR, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 已推送到 GitHub")
            return True
        else:
            print(f"❌ Push 失敗: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Git 錯誤: {e}")
        return False

def main():
    """主程式"""
    print("🐾 動物部落格文章生成器")
    print("=" * 40)
    
    # 載入動物
    load_animals()
    
    # 取得下一個動物
    animal = get_next_animal()
    print(f"\n準備生成文章: {animal['name']} ({animal['location']})")
    
    # 生成文章
    content = generate_full_article(animal)
    
    # 儲存文章
    save_article(animal, content)
    
    # 推送到 GitHub
    print("\n📤 推送到 GitHub...")
    push_to_github()
    
    print("\n✨ 完成！")

if __name__ == "__main__":
    main()