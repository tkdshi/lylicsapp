#!/usr/bin/env python
# coding: utf-8

# In[1]:


# 1曲ぶんの歌詞を作成

import sqlite3
import csv
import pandas as pd
from bs4 import BeautifulSoup
import collections
import re
import jaconv
import sys
import requests
import json
import math
import pickle
import scipy.stats
import MeCab
import subprocess
#from apiclient.discovery import build
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import wordnet
# pip install googletrans==4.0.0-rc1
from googletrans import Translator
import pykakasi
youtube_key = 'AIzaSyC3KcLEIhfsyDitsKdXJC-kk0DgM9Nd-GY'
youtube_key = 'AIzaSyDrFZHWXx8UtDWKSmJ6cGF0a49VhvMnYRg'


# BeautifulSoupでHTMLをパースする
def ParseHtmlFile(html_file):
    return BeautifulSoup(html_file, 'html.parser')


# ひらがなテキストを正規表現でモーラ毎のリストに変換。引用　https://qiita.com/shimajiroxyz/items/9580f185217fc9738f33
def getmora(text):
    # 「((ウ段＋「ァ/ィ/ェ/ォ」)|(イ段（「イ」を除く）＋「ャ/ュ/ェ/ョ」)|( 「テ/デ」＋「ィ/ュ」)|(大文字カナ))(「ー/ッ/ン」の連続文字列（０文字含む）)」の正規表現
    c1 = '[うくすつぬふむゆるぐずづぶぷゔウクスツヌフムユルグズヅブプヴ][ぁぃぇぉァィェォ]'  # ウ段＋「ァ/ィ/ェ/ォ」
    c2 = '[いきしちにひみりぎじぢびぴイキシチニヒミリギジヂビピ][ゃゅぇょャッュェョ]'  # イ段（「イ」を除く）＋「ャ/ュ/ェ/ョ」
    c3 = '[てでテデ][ぃゅィュ]'  # 「テ/デ」＋「ィ/ュ」
    c4 = '[ぁ-ヴー]'  # かな1文字 + 長音
    try:
        cond = '(' + c1 + '|' + c2 + '|' + c3 + '|' + c4 + ')'
        re_mora = re.compile(cond)
        return re_mora.findall(text)
    except:
        return []


def getmora_last(text):
    text_list = text.split()

    t = ""
    for l in text_list:
        t = t + l[-1]
    # 「((ウ段＋「ァ/ィ/ェ/ォ」)|(イ段（「イ」を除く）＋「ャ/ュ/ェ/ョ」)|( 「テ/デ」＋「ィ/ュ」)|(大文字カナ))(「ー/ッ/ン」の連続文字列（０文字含む）)」の正規表現
    c1 = '[うくすつぬふむゆるぐずづぶぷゔウクスツヌフムユルグズヅブプヴ][ぁぃぇぉァィェォ]'  # ウ段＋「ァ/ィ/ェ/ォ」
    c2 = '[いきしちにひみりぎじぢびぴイキシチニヒミリギジヂビピ][ゃゅぇょャッュェョ]'  # イ段（「イ」を除く）＋「ャ/ュ/ェ/ョ」
    c3 = '[てでテデ][ぃゅィュ]'  # 「テ/デ」＋「ィ/ュ」
    c4 = '[ぁ-ヴー]'  # かな1文字 + 長音

    text = t
    try:
        cond = '(' + c1 + '|' + c2 + '|' + c3 + '|' + c4 + ')'
        re_mora = re.compile(cond)
        # print(re_mora.findall(text))
        return re_mora.findall(text)
    except:
        # print([])
        return []


# ひらがなテキストを実際の発音に変換
def replace_text(text):
    la = list('あかさたなはまやらわがざだばぱアカサタナハマヤラワガザダバパ')
    li = list('いきしちにひみりぎじびぴイキシチニヒミリギジビピ')
    lu = list('うくすつぬふむゆるゔぐずぶぷウクスツヌフムユルグズヅブプヴ')
    le = list('えけせてねへめれげぜでべぺエケセテネヘメレゲゼデベペ')
    lo = list('おこそとのほもよろごぞどぼぽオコソトノホモヨロゴゾドボポ')

    for l in le:
        pattern_before = '[' + l + '][い]'
        text = re.sub(pattern_before, l + "え", text)
        pattern_before = '[' + l + '][ー]'
        text = re.sub(pattern_before, l + "え", text)

    for l in lo:
        pattern_before = '[' + l + '][う]'
        text = re.sub(pattern_before, l + "お", text)
        pattern_before = '[' + l + '][ー]'
        text = re.sub(pattern_before, l + "お", text)

    for l in la:
        pattern_before = '[' + l + '][ー]'
        text = re.sub(pattern_before, l + "あ", text)

    for l in li:
        pattern_before = '[' + l + '][ー]'
        text = re.sub(pattern_before, l + "い", text)

    for l in lu:
        pattern_before = '[' + l + '][ー]'
        text = re.sub(pattern_before, l + "う", text)

    return text


# HTML歌詞ファイルのルビを除去=通常の歌詞に
def RemoveRuby(soup):
    soup_arg = soup
    tag = soup_arg.find_all(class_='rt')

    for t in tag:
        t.decompose()

    return soup_arg.get_text()


# HTML歌詞ファイルでルビが付与されている部分のタグを削除
def RemoveLylics(soup):
    soup_arg = soup
    tag = soup_arg.find_all(class_='rb')

    for t in tag:
        t.decompose()

    return soup_arg.get_text()


# カタカナをひらがなの全角表記にする　https://pypi.org/project/jaconv/0.2/
def ReplaceToHiragana(str):
    return jaconv.kata2hira(str)


# 日本語の各モーラの出現回数を数える
def countjapanmora(list):
    japan_mora = ['あ', 'い', 'う', 'え', 'お', 'や', 'ゆ', 'よ',
                  'か', 'き', 'く', 'け', 'こ', 'きゃ', 'きゅ', 'きょ',
                  'が', 'ぎ', 'ぐ', 'げ', 'ご', 'ぎゃ', 'ぎゅ', 'ぎょ',
                  'さ', 'し', 'す', 'せ', 'そ', 'しゃ', 'しゅ', 'しょ',
                  'ざ', 'じ', 'ず', 'ぜ', 'ぞ', 'じゃ', 'じゅ', 'じょ',
                  'た', 'ち', 'つ', 'て', 'と', 'ちゃ', 'ちゅ', 'ちょ',
                  'だ', 'NaN', 'NaN', 'で', 'ど', 'NaN', 'NaN', 'NaN',
                  'な', 'に', 'ぬ', 'ね', 'の', 'にゃ', 'にゅ', 'にょ',
                  'は', 'ひ', 'ふ', 'へ', 'ほ', 'ひゃ', 'ひゅ', 'ひょ',
                  'ぱ', 'ぴ', 'ぷ', 'ぺ', 'ぽ', 'ぴゃ', 'ぴゅ', 'ぴょ',
                  'ば', 'び', 'ぶ', 'べ', 'ぼ', 'びゃ', 'びゅ', 'びょ',
                  'ま', 'み', 'む', 'め', 'も', 'みゃ', 'みゅ', 'みょ',
                  'ら', 'り', 'る', 'れ', 'ろ', 'りゃ', 'りゅ', 'りょ',
                  'わ', 'NaN', 'NaN', 'NaN', 'NaN', 'NaN', 'NaN', 'NaN',
                  'ん', 'っ', 'ー', 'OTHER', 'NaN', 'NaN', 'NaN', 'NaN']

    #mora_count = [0 if japan_mora[i] != '' else 'NaN' for i in range(len(japan_mora))]
    mora_count = [0 if japan_mora[i] !=
                  '' else 0 for i in range(len(japan_mora))]
    for l in list:
        l = ReplaceToHiragana(l)

        try:
            mora_count[japan_mora.index(l)] += 1
        except:
            mora_count[japan_mora.index('OTHER')] += 1
    return mora_count


def countjapanmora_last(list):
    japan_mora = ['あ', 'い', 'う', 'え', 'お', 'や', 'ゆ', 'よ',
                  'か', 'き', 'く', 'け', 'こ', 'きゃ', 'きゅ', 'きょ',
                  'が', 'ぎ', 'ぐ', 'げ', 'ご', 'ぎゃ', 'ぎゅ', 'ぎょ',
                  'さ', 'し', 'す', 'せ', 'そ', 'しゃ', 'しゅ', 'しょ',
                  'ざ', 'じ', 'ず', 'ぜ', 'ぞ', 'じゃ', 'じゅ', 'じょ',
                  'た', 'ち', 'つ', 'て', 'と', 'ちゃ', 'ちゅ', 'ちょ',
                  'だ', 'NaN', 'NaN', 'で', 'ど', 'NaN', 'NaN', 'NaN',
                  'な', 'に', 'ぬ', 'ね', 'の', 'にゃ', 'にゅ', 'にょ',
                  'は', 'ひ', 'ふ', 'へ', 'ほ', 'ひゃ', 'ひゅ', 'ひょ',
                  'ぱ', 'ぴ', 'ぷ', 'ぺ', 'ぽ', 'ぴゃ', 'ぴゅ', 'ぴょ',
                  'ば', 'び', 'ぶ', 'べ', 'ぼ', 'びゃ', 'びゅ', 'びょ',
                  'ま', 'み', 'む', 'め', 'も', 'みゃ', 'みゅ', 'みょ',
                  'ら', 'り', 'る', 'れ', 'ろ', 'りゃ', 'りゅ', 'りょ',
                  'わ', 'NaN', 'NaN', 'NaN', 'NaN', 'NaN', 'NaN', 'NaN',
                  'ん', 'っ', 'ー', 'OTHER', 'NaN', 'NaN', 'NaN', 'NaN']

    #mora_count = [0 if japan_mora[i] != '' else 'NaN' for i in range(len(japan_mora))]
    mora_count = [0 if japan_mora[i] !=
                  '' else 0 for i in range(len(japan_mora))]
    for l in list:
        l = ReplaceToHiragana(l)

        try:
            mora_count[japan_mora.index(l)] += 1
        except:
            mora_count[japan_mora.index('OTHER')] += 1
    return mora_count


def normalize_df_mora_count(df):
    return df / df.sum().sum()


# 各モーラの出現回数の結果をデータフレームに変換
def CountListToDf(list):
    # print(list)
    df_row_name = ['-', 'k-', 'g-', 's-', 'z-', 't-', 'd-',
                   'n-', 'h-', 'b-', 'p-', 'm-', 'r-', 'w-', 'exp(ん,っ,ー,etc)']
    df = pd.DataFrame({'-a': [],
                       '-i': [],
                       '-u': [],
                       '-e': [],
                       '-o': [],
                       '-ja': [],
                       '-ju': [],
                       '-jo': [],
                       })

    i = 0

    while (i < len(list) / 8):
        df.loc[df_row_name[i]] = list[(8 * i):(8 + (8 * i))]
        i += 1
    df = normalize_df_mora_count(df)

    df = df.fillna(0)
    # print(df)
    return df


# オノマトペの選考研究に基づくスコアの計算
def calc_score(df_all):
    research_score_df = []
    file = ['s1.csv', 's2.csv', 's3.csv', 's4.csv']
    for f in file:
        research_score_df.append(pd.read_csv(f, index_col=0))

    score_all = []

    for df in df_all:
        score = []
        for df_score in research_score_df:
            s = df * df_score
            score.append(s.sum().sum())
        score_all.append(score)

        # print(score_all)
    return score_all


# オノマトペの選考研究に基づくスコアの計算
def calc_score_pro(df_all):
    # 濁音の割合
    def score_1(df):
        s = df.sum(axis=1)
        # print(s)
        score = s[2].sum() + s[4].sum() + s[6].sum() + s[9].sum()
        return score

    # 破裂音の割合（カタバガダパ）行
    def score_2(df):
        s = df.sum(axis=1)
        # print(s)
        score = s[1].sum() + s[2].sum() + s[5].sum() + \
            s[6].sum() + s[9].sum() + s[10].sum()
        return score

    # 拗音（ャュョ）の割合
    def score_3(df):
        s = df.sum()
        # print(s)
        score = s[5:].sum()
        return score

    # サ行（息が入る）
    def score_4(df):
        s = df.sum(axis=1)
        # print(s)
        score = s[3].sum()
        return score

    # マ行ナ行ヤ行
    def score_5(df):
        s = df.sum(axis=1)
        # print(s)
        score = s[3].sum()
        return score

    # ヤ行あり母音割合
    def score_a1(df):
        df = df[:-1]
        s = df.sum()
        # print(s)
        score = s[0].sum() + s[5].sum()
        return score

    def score_i1(df):
        df = df[:-1]
        s = df.sum()
        # print(s)
        score = s[1].sum()
        return score

    def score_u1(df):
        df = df[:-1]
        s = df.sum()
        # print(s)
        score = s[2].sum() + s[6].sum()
        return score

    def score_e1(df):
        df = df[:-1]
        s = df.sum()
        # print(s)
        score = s[3].sum()
        return score

    def score_o1(df):
        df = df[:-1]
        s = df.sum()
        # print(s)
        score = s[4].sum() + s[7].sum()
        return score

    def score_a2(df):
        df = df[:-1]
        s = df.sum()
        # print(s)
        score = s[0].sum()
        return score

    def score_u2(df):
        df = df[:-1]
        s = df.sum()
        # print(s)
        score = s[2].sum()
        return score

    def score_o2(df):
        df = df[:-1]
        s = df.sum()
        # print(s)
        score = s[4].sum()
        return score

    score_all = []

    for df in df_all:
        score = []
        s1 = score_1(df)
        s2 = score_2(df)
        s3 = score_3(df)
        s4 = score_4(df)
        s5 = score_5(df)
        sa1 = score_a1(df)
        si1 = score_i1(df)
        su1 = score_u1(df)
        se1 = score_e1(df)
        so1 = score_o1(df)
        sa2 = score_a2(df)
        su2 = score_u2(df)
        so2 = score_o2(df)
        score = [s1, s2, s3, s4, s5, sa1, si1, su1, se1, so1, sa2, su2, so2]
        # score.append(s.sum().sum())
        score_all.append(score)

        # print(score_all)
    return score_all


# データフレームが入ったリストを渡し、平均を返す
def sum_df_mora_count(df_all):
    flag = 0
    for df in df_all:
        # 1曲目だった
        if flag == 0:
            dfmc = df.copy()
            flag = 1
        else:
            dfmc += df
    # print(dfmc / len(df_all))
    return dfmc / len(df_all)

# youtubeのURLから情報を取得する


def youtube_analize(youtube_list):
    view = []
    like = []
    dislike = []
    comment = []
    for l in youtube_list:
        if l == None:
            view.append(None)
            like.append(None)
            dislike.append(None)
            comment.append(None)
            continue
        else:

            # print(l)
            try:
                str = l.split('&')[0]  # 先頭の動画を取得
                str = str.replace('https://youtu.be/', '')
                str = str.strip()
                # print(str)

                url = 'https://www.googleapis.com/youtube/v3/videos?id=' + str + '&key=' + \
                    youtube_key + '&part=snippet,contentDetails,statistics,status'
                # print(url)

                response = requests.get(url)
                jsonData = response.json()
                json_statistics = jsonData['items'][0]['statistics']
                # print(json_statistics)
                view.append(
                    json_statistics['viewCount'] if 'viewCount' in json_statistics else None)
                like.append(
                    json_statistics['likeCount'] if 'likeCount' in json_statistics else None)
                #dislike.append(json_statistics['dislikeCount'] if 'dislikeCount' in json_statistics != None else None)
                comment.append(
                    json_statistics['commentCount'] if 'commentCount' in json_statistics != None else None)
            except:
                view.append(None)
                like.append(None)
                dislike.append(None)
                comment.append(None)
    #print([view, like, dislike, comment])
    return [view, like, dislike, comment]


def tfidf_list_to_pd(tfidf_list):
    tfidfpd = pd.DataFrame(tfidf_list)
    tfidfpd.columns = itemlist
    # print(tfidfpd)

    #print((tfidfpd.iloc[0, :]).dot(tfidfpd.iloc[1, :]))
    return tfidfpd


def tfidfpd_to_cosnumpd(tfidfpd):
    cosnum = [0] * (len(tfidfpd)+1)
    # print(len(lyliclist))
    for ref_file in range(len(tfidfpd)-1):
        for j in range(ref_file+1, len(sim[ref_file])):
            #print(ref_file,j, sim[ref_file][j])
            cosnum[ref_file] += (tfidfpd.iloc[ref_file, :]
                                 ).dot(tfidfpd.iloc[j, :])
            cosnum[j] += (tfidfpd.iloc[ref_file, :]).dot(tfidfpd.iloc[j, :])


# 歌詞の配列を単語ごとで分析。TFIDFの大きさで色を変更
def get_html_cosnumpd_word(lylics_list, tfidfpd):
    html = ''
    i = 0
    j = 0
    for l in lylics_list:
        for ll in l:
            head = 1
            flag = 0
            html = html + '<p data-match="' + str(cosnumpd['minmax'][j]) + '">'
            for lll in ll:
                try:
                    tfidf = tfidfpd[lll[0]][i]
                except:
                    tfidf = 0.0
                # 英字の場合は半角スペースを付与
                ## not先頭 and(前が英語 or 自身が英語)
                asc = lll[0].isascii()
                if head != 1 and (flag == 1 or asc):
                    html = html + '<div data-part="' + lll[1] + '" style="background-color: rgba(255,255,0,' + str(
                        tfidf) + ');">' + '&nbsp' + lll[0] + '</div>'
                else:
                    html = html + '<div data-part="' + lll[1] + '" style="background-color: rgba(255,255,0,' + str(
                        tfidf) + ');">' + lll[0] + '</div>'
                flag = 1 if asc else 0
                head = 0
            html = html + '</p>'
            i += 1
        j += 1
    return html


# 重要語の高速化（TFIDF取得）
def get_tfidfdata(lylics_list):
    lst = []
    for l in lylics_list:
        lst.extend(l.split(" "))
    # 全データの曲数
    lst = [i for i in lst if i != '']
    songs_count = 259764
    # 各単語の登場回数(全データ)
    series_int = pd.read_pickle('series_int.pkl')
    series_int_dict = series_int.to_dict()
    c = collections.Counter(lst)
    d = dict(c)
    ll = list(d.keys())
    tf_under = sum(d.values())

    tf = list(d.values())
    tf = [i/tf_under for i in tf]
    idf = []
    for lll in ll:
        if lll in series_int_dict:
            idf_value = math.log10(songs_count/series_int_dict[lll]) + 1
        else:
            idf_value = 1
        idf.append(idf_value)

    tfidf = []
    for i in range(len(tf)):
        tfidf_value = tf[i] * idf[i]
        tfidf.append(tfidf_value)
    # print(c)
    # print(lst)
    # print(ll)
    # print(idf)
    # print(tfidf)

    return dict(zip(ll, tfidf))  # TF-IDFの辞書


# 歌詞の配列を単語ごとで分析。TFIDFの大きさで色を変更（全曲）（重要語）
def get_html_cosnumpd_word_all(lylics_list, tfidfpd):
    html = ''
    j = 0
    for l in lylics_list:
        for ll in l:
            i = 0
            html = html + '<p data-match="' + str(cosnumpd['minmax'][j]) + '">'
            for lll in ll:
                try:
                    tfidf = tfidfpd[lll[0]][0]
                except:
                    tfidf = 0.0
                # 英字の場合は半角スペースを付与
                if i != 0 and lll[0].isascii():
                    html = html + '<div data-part="' + lll[1] + '" style="background-color: rgba(255,255,0,' + str(
                        tfidf) + ');">' + '&nbsp' + lll[0] + '</div>'
                else:
                    html = html + '<div data-part="' + lll[1] + '" style="background-color: rgba(255,255,0,' + str(
                        tfidf) + ');">' + lll[0] + '</div>'
                i += 1
            html = html + '</p>'

        j += 1
    return html

# 歌詞の配列を単語ごとで分析。TFIDFの大きさで色を変更（全曲）（重要語）（辞書使用）


def get_html_cosnumpd_word_use_dict(lylics_list, itemlist):
    html = ''
    dic = get_tfidfdata(itemlist)
    #i = 0
    j = 0
    for l in lylics_list:
        for ll in l:
            head = 1
            flag = 0
            html = html + '<p data-match="' + str(cosnumpd['minmax'][j]) + '">'
            for lll in ll:
                tfidf = dic[lll[0]]
                # 英字の場合は半角スペースを付与
                ## not先頭 and(前が英語 or 自身が英語)
                asc = lll[0].isascii()
                if head != 1 and (flag == 1 or asc):
                    html = html + '&nbsp' + '<div data-part="' + lll[1] + '" style="background-color: rgba(255,255,0,' + str(
                        tfidf) + ');">' + lll[0] + '</div>'
                else:
                    html = html + '<div data-part="' + lll[1] + '" style="background-color: rgba(255,255,0,' + str(
                        tfidf) + ');">' + lll[0] + '</div>'
                flag = 1 if asc else 0
                head = 0
            html = html + '</p>'

        j += 1
    return html


# 文ごと
def get_html_cosnumpd_sentence(lylics_list):
    html = ''
    i = 0
    j = 0
    for l in lylics_list:
        for ll in l:
            head = 1
            flag = 0
            html = html + '<p><div style="background-color: rgba(255,255,0,' + str(
                cosnumpd['minmax'][j]) + ') !important;">'
            for lll in ll:
                try:
                    tfidf = tfidfpd[lll[0]][i]
                except:
                    tfidf = 0.0
                asc = lll[0].isascii()
                if head != 1 and (flag == 1 or asc):
                    html = html + '&nbsp' + '<div data-part="' + \
                        lll[1] + '">' + lll[0] + '</div>'
                else:
                    html = html + '<div data-part="' + \
                        lll[1] + '">' + lll[0] + '</div>'
                flag = 1 if asc else 0
                head = 0
            html = html + '</div></p>'
            i += 1
            j += 1
    return html


def tfidf_list_to_pd(tfidf_list):
    tfidfpd = pd.DataFrame(tfidf_list)
    tfidfpd.columns = itemlist
    # print(tfidfpd)

    #print((tfidfpd.iloc[0, :]).dot(tfidfpd.iloc[1, :]))
    return tfidfpd


def tfidfpd_to_cosnumpd(tfidfpd):
    cosnum = [0] * (len(tfidfpd)+1)
    print(len(lyliclist))
    for ref_file in range(len(tfidfpd)-1):
        for j in range(ref_file+1, len(sim[ref_file])):
            #print(ref_file,j, sim[ref_file][j])
            cosnum[ref_file] += (tfidfpd.iloc[ref_file, :]
                                 ).dot(tfidfpd.iloc[j, :])
            cosnum[j] += (tfidfpd.iloc[ref_file, :]).dot(tfidfpd.iloc[j, :])

    print(cosnum)

    cosnumpd = pd.DataFrame(cosnum)

    cosnumpd['std'] = scipy.stats.zscore(cosnumpd.iloc[:, 0], axis=0)
    cosnumpd['minmax'] = (cosnumpd.iloc[:, 0]-cosnumpd.iloc[:, 0].min()) / \
        (cosnumpd.iloc[:, 0].max()-cosnumpd.iloc[:, 0].min())

    cosnumpd['text'] = texts

    return cosnumpd


def wakati(lyliclist):
    n = 0
    wakati = []
    lylicstr = ""
    for l in lyliclist[n:n+1]:

        for ll in l:
            str_w = ""

            for lll in ll:
                str_w = str_w + lll[0] + " "
                lylicstr = lylicstr + lll[0]
                #i += 1
            lylicstr = lylicstr + "\n"
            wakati.append(str_w)
    return lylicstr, wakati  # str,list


def get_html_ruigigo(lylics_list):
    html = ''
    i = 0
    j = 0
    for l in lylics_list:
        for ll in l:
            html = html + '<p>'
            for lll in ll:
                try:
                    tfidf = tfidfpd[lll[0]][i]
                except:
                    tfidf = 0.0
                #html = html + '<div data-part="' + lll[1] + '" data-tfidf="' + str(tfidf) +'">'+ lll[0] +'</div>'
                ruigigo(lll[0])
                html = html + '<div data-part="' + \
                    lll[1] + '">' + lll[0] + '</div>'
            html = html + '</p>'
            i += 1
            j += 1
    return html


def checkAlnum(word):
    alnum = re.compile(r'^[a-zA-Z0-9]+$')
    result = alnum.match(word) is not None
    return result


def ruigigo2(keyword):

    key = keyword

    # synset:概念id
    if checkAlnum(key):
        synsets = wordnet.synsets(key, lang='eng')
    else:
        synsets = wordnet.synsets(key, lang='jpn')

    output = ""
    output += "<h2>" + key + "</h2>"

    for s in synsets:
        # print(s, s.definition())

        translator = Translator()
        '''
        for h in s.hypernyms():  # 上位語
            # print("\t", s, "->", h, h.definition())
            output += '<p><b>' + translator.translate(h.definition(), src='en',
                                                                            dest='ja').text + "</b></p>"
            output += "<p>" + h.definition() + "</p>"
            # print("\t", h.lemma_names(lang='jpn'))
            output += '<ul class="list-group list-group-horizontal"><li class="list-group-item item-upper">' + '</li><li class="list-group-item item-upper">'.join(h.lemma_names(lang='jpn')) + '</li><li class="list-group-item item-upper">' + '</li><li class="list-group-item item-upper">'.join(
                h.lemma_names(lang='eng')) + "</li></ul>"
        '''
        # main語
        output += s.definition()
        output += '<p><b>' + translator.translate(s.definition(), src='en',
                                                  dest='ja').text + "</b></p>"
        output += "<p>" + s.definition() + "</p>"

        '''
        for h in s.hyponyms():  # 下位語
            #print("\t", s, "->", h, h.definition())
            output += "<h5>" + translator.translate(h.definition(), src='en', dest='ja').text + "</h5>"
            output += "<q>" + h.definition() + "</q>"
            #print("\t", h.lemma_names(lang='jpn'))
            output += '<ul class="list-group list-group-horizontal"><li class="list-group-item item-upper">' + '</li><li class="list-group-item item-upper">'.join(h.lemma_names(lang='jpn')) + '</li><li class="list-group-item item-upper">' + '</li><li class="list-group-item item-upper">'.join(h.lemma_names(lang='eng')) + "</li></ul>"
        '''

        # print(s.lemma_names(lang='jpn'))
        '''
        output += '<ul class="list-group list-group-horizontal"><li class="list-group-item item-main">' + '</li><li class="list-group-item item-main">'.join(
            s.lemma_names(
                lang='jpn')) + '</li><li class="list-group-item item-main">' + '</li><li class="list-group-item item-main">'.join(
            s.lemma_names(lang='eng')) + "</li></ul>"
        '''
        output += '<ul class="list-group list-group-horizontal"><li class="list-group-item item-main">' + '</li><li class="list-group-item item-main">'.join(
            s.lemma_names(
                lang='jpn')) + '</li><li class="list-group-item item-main">' + '</li><li class="list-group-item item-main">'.join(
            s.lemma_names(lang='eng')) + "</li></ul>"

    if output == "<h2>" + key + "</h2>":
        output = ''
    return output


conn = sqlite3.connect("wnjpn.db")


def ruigigo(word):

    # 問い合わせしたい単語がWordnetに存在するか確認する
    cur = conn.execute("select wordid from word where lemma='%s'" % word)
    word_id = 99999999  # temp
    for row in cur:
        word_id = row[0]

    # Wordnetに存在する語であるかの判定
    if word_id == 99999999:
        #print("「%s」は、Wordnetに存在しない単語です。" % word)
        return ''

    # 入力された単語を含む概念を検索する
    cur = conn.execute("select synset from sense where wordid='%s'" % word_id)
    synsets = []
    output = ''
    output += "<h2>" + word + "</h2>"
    for row in cur:
        synsets.append(row[0])

    # 概念に含まれる単語を検索して画面出力する
    no = 1
    for synset in synsets:
        cur1 = conn.execute(
            "select name from synset where synset='%s'" % synset)
        for row1 in cur1:
            #print("%sつめの概念 : %s" %(no, row1[0]))
            output += row1[0]
        cur2 = conn.execute(
            "select def from synset_def where (synset='%s' and lang='jpn')" % synset)
        sub_no = 1
        output += "<ul>"
        for row2 in cur2:
            output += "<li><p>"+row2[0]+"</p></li>"
            sub_no += 1
        output += "</ul>"
        cur3 = conn.execute(
            "select wordid from sense where (synset='%s' and wordid!=%s)" % (synset, word_id))
        sub_no = 1
        #output += '<ul class="list-group list-group-horizontal">'
        output += '<div class="container">'
        for row3 in cur3:
            target_word_id = row3[0]
            cur3_1 = conn.execute(
                "select lemma from word where wordid=%s" % target_word_id)
            for row3_1 in cur3_1:
                #print("類義語%s : %s" % (sub_no, row3_1[0]))
                #output += '<li class="list-group-item item-main">' +row3_1[0] + '</li>'
                output += '<button type="button" class="btn btn-light">' + \
                    row3_1[0] + '</button>'
                sub_no += 1
        output += '</div>'
        #output += "</ul>"
        # print("\n")
        no += 1

    return output


def list_to_ruby(lyliclist):
    out = ""
    for l in lyliclist:
        for ll in l:

            for lll in ll:
                # print(lll,lll[2])
                if lll[2] == "*":

                    # オブジェクトをインスタンス化
                    kakasi = pykakasi.kakasi()
                    # モードの設定：J(Kanji) to H(Hiragana)
                    kakasi.setMode('J', 'H')

                    # 変換して出力
                    conv = kakasi.getConverter()
                    out += conv.do(lll[0])

                else:
                    out += lll[2]
            out += "\n"

    return out


# In[2]:


s1 = pd.read_csv('s1.csv')
s2 = pd.read_csv('s2.csv')
s3 = pd.read_csv('s3.csv')
s4 = pd.read_csv('s4.csv')

# input

print('開始曲数:(1以上）')
#start_num = int(input()) - 1
print('終了曲数:')
#final_num = int(input()) - 1

writer_unique = []
basic_lylic = []
'''
#df_all = pd.read_pickle('../html_analize/df_vocaloid.pkl')
df_all = pd.read_pickle('../html_analize/df_all_new_jpn.pkl')
#df_all = pd.read_pickle('ado.pkl')
df_all = df_all.sort_index()
df_all = df_all.reset_index()

title = list(df_all['title'])
title_ruby = list(df_all['title_ruby'])
writer = list(df_all['writer'])
youtube = list(df_all['youtube'])
# print(youtube)
tag = list(df_all['tag'])
release_data = list(df_all['release_data'])
html_hira = list(df_all['lylics_html_hiragana'])
html_eng = list(df_all['lylics_html_romaji'])

df_all['writer'].fillna('Unknown')
'''
df_mora_count_artist = []

df_mora_count_tmp = []
df_mora_count_song = []
df_mora_count_title = []


# youtube取得
youtube_index = ['再生数', '高評価数', '低評価数', 'コメント数']
# view, like, dislike, comment = youtube_analize(youtube)
#youtube_data = youtube_analize(youtube[start_num:final_num + 1])
#lylics_score_youtube_df = pd.DataFrame([list(x) for x in zip(*youtube_data)], columns=youtube_index)
# print(lylics_score_youtube_df)


# In[3]:


ans_all = []
start_num = 0
final_num = start_num
flag = 1


#soup = ParseHtmlFile(html_f)
#basic_text = RemoveRuby(soup)

basic_text = '''この声でこの音で
君と共に駆け抜ける
さあ

青く晴れたとある夏の日
今日も変わらないありふれた世界
一人きりの君とここらで
巡り合ったんだ

君は真面目で創造的
だけどいつも少し不安げ
そんな君と二人ここまで
歩んできたんだ

君の未来が
もっと輝くように
ずっと願うから

この声でこの音で
君と同じ想いを
ずっと ずっと
力の限り歌うよ

この声でこの音で
君がくれた言葉が
きっと　きっと
僕らの世界を描くよ
白く光るとある冬の日
広がりだす新しい世界
君が追い求める未来が
近づいていった

君の世界が
もっと広がるように
ずっと願うから

この声でこの音で
君の熱い想いを
ずっと ずっと
力の限り歌うよ

この声でこの音で
君がくれた言葉が
もっと もっと
遠くの世界へ

君のその想いが
未来へと届いていく
新しい世界まで
想いが高まっていく

君のその言葉が
遠くへと響いていく
新しい世界まで
その声を追いかけていく

この声でこの音で
君がくれた言葉から
この声でこの音で
君の今を照らすから
さあ

この声でこの音で
君と同じ想いを
ずっと ずっと
力の限り歌うよ

この声でこの音で
君がくれた言葉が
きっと　きっと
僕らの世界を描くよ

この声でこの音で
君がくれた言葉から
この声でこの音で
君の未来を照らすから
さあ'''

'''basic_text=
快晴の空 輝く大地
新しいステージへ
キミは真っ先に
飛び出していった

青色のシグナル灯り
スタートライン踏んで
キミは進み出した

掻き鳴らすエンジン音
キミを掻き回すサーキット
疾る風に乗って
加速していった

気がつけばいつの間にか
最前線で飛ばし続ける
キミに夢中になったんだ

キミが降り立つこの場所で
僕らの声が重なり　
想いとなり果てしない
力になったんだ

未来へと走り続け
最速で道を駆けるんだ
僕らと目指し続けている
新たな世界へ！

行き先は一つだけさ
この道を進んでいくのさ
アタシが最高の笑顔で
背中を押すから！


陽が煌く空 続く大地
キミ色のステージで
僕らの想い乗せて
走り続けた

同じ景色繰り返し
スタートライン踏んで
キミは進み続けた　

響き渡るエンジン音
チャンス見極め踏むアクセル
疾る風はさらに強まっていった

誰にも止められないまま
感情を抑えられないまま
キミをただ見ていた

キミが降り立つこの地球の
どこかで僕ら繋がり
キミの強い熱情を
受け止めていくんだ

未来へと走り続け
最高の現実を描くんだ
僕らと想い続けている
理想の世界へ！

行き先は変わらないさ
いつまでも進んでいくのさ
アタシが最高の笑顔で
キミを照らすから！


もしアタシが天使なら
次元超えていけるのなら
きっと翼羽ばたかせ
キミに会いに行くよ

キミの笑顔のために
僕らの願い届け
ずっとキミがいつもいつまでも
輝けるように


未来へと走り続け
この場所で虹を架けるんだ
僕らと走り続けていく
新たな世界へ！

行き先はそばにあるさ
この道をいま走りきるんだ
キミと僕らのこの想いが
虹を架けるよ！


いま輝くキミを抱きしめ
次のステージへ！'''


basic_text = '''きらきら、光ってるはずなんだ

キャパシティオーバー
てんてこまいの毎日だ
頭こんがらがって warning warning

でっかい月の上にウサギがいるんだっけ？
宇宙旅行にパスポートって要りますか

僕らが歩いていくセカイの明日はどんな色？
君と僕で描いていくふたりいろ

I shall checkmate 君を checkmate
会いたい時には会いに行くよ
地球の裏から夢の中まで
ひらひら、スカートが揺れる

escort 君を escort
マニュアル通りじゃつまんないでしょ？
不安の数だけ希望があるってこと
きらきら、光ってるはずなんだ

エマージェンシーじゃん
なんでもありのアイドルだ
常識もグラついちゃって panic panic

深海、海の底でマーメイドが恋をしたって？
嘘か本当か確かめに行きませんか

僕らの暮らしてるセカイは人ひとりひとつの色
それはお父さんお母さんのあいのいろ

I shall checkmate 君を checkmate
雨降り天気でも会いに行くよ
果報が来るまで寝とけばいいってマジ？
いやいや、待てるわけなくね

絶好調、もうずっと絶好調
片道切符で構わないでしょ？
無理も通せば道理がなんとやら
高く高く跳べる気がしてるんだ

胸の奥がキュッとなる
消えない消せない過去も笑えるように
未来が僕らを呼んでる
ほら踊れる曲は踊っとくのが楽しむコツ

I shall checkmate 君を checkmate
会いたい時には会いに行くよ
机の奥から22世紀まで
ふらふら、旅してる途中

escort 君を escort
マニュアル通りじゃつまんないでしょ？
不安の数だけ希望があるってこと
高く高く跳べる気がしてる
きらきら、光ってるはずなんだ'''

basic_lylic.append(basic_text)
#soup = ParseHtmlFile(html_f)
#hira_text = RemoveLylics(soup)
#hira_text = replace_text(hira_text)

#hira_text_title_ruby = title_ruby[i]
# print(hira_text)
'''
#ローマ字歌詞
html_f = html_eng[0]
soup = ParseHtmlFile(html_f)
eng_text = RemoveLylics(soup)
print(eng_text)
'''

#mora_list = getmora(hira_text)
#mora_list_last = getmora_last(hira_text)

print("===")
# print(mora_list)
print("===")
# print(mora_list_last)

ans = []
count = 0
t = MeCab.Tagger()
for l in basic_text.split('\n'):
    result = t.parse(l).replace("\t", ",").splitlines()
    ans_sentence = []
    for ll in result:

        lst = ll.split(",")
        # print(lst)
        ans_tmp = []
        if lst != [''] and lst[0] != "EOS" and lst[1] != '記号':
            ans_tmp.append(lst[0])
            ans_tmp.append(lst[1])
            ans_tmp.append(lst[-1])
            ans_tmp.append(count)
            ans_tmp.append(1)
            ans_sentence.append(ans_tmp)
            count += 1
        else:
            if(ans_sentence != []):
                ans.append(ans_sentence)
            ans_sentence = []
            count = 0
            continue
ans_all.append(ans)
# print(ans_all)


# with open("ans.pkl", "wb") as f:
#    pickle.dump(ans_all, f) #保存


# In[ ]:


# In[4]:


#wakati_all = pd.read_pickle('wakati_all.pkl')


# lyliclistから元の歌詞を取り出す
lyliclist = ans_all


# 分かち書き
lylicstr, wakati = wakati(lyliclist)


# wakati_all.append(" ".join(wakati)) #現在の曲の分かち書き情報を追加

vectorizer_count = CountVectorizer(token_pattern="(?u)\\b\\w+\\b")
vectorizer_count.fit(wakati)
X_count = vectorizer_count.transform(wakati)
tf_list = X_count.toarray()


vectorizer_x = TfidfVectorizer(norm="l2", token_pattern="(?u)\\b\\w+\\b")
vectorizer_x.fit(wakati)
X = vectorizer_x.transform(wakati)
tfidf_list = X.toarray()
# 語彙を抽出
itemlist = vectorizer_x.get_feature_names()


'''
vectorizer_x_all = TfidfVectorizer(norm="l2", token_pattern="(?u)\\b\\w+\\b")
vectorizer_x_all.fit(wakati_all)
X_all = vectorizer_x_all.transform(wakati_all)
tfidf_list_all = X.toarray()
#語彙を抽出
itemlist_all = vectorizer_x_all.get_feature_names()
'''


texts = lylicstr.split("\n")

# print("# of vocabulary: " + str(len(vec.vocabulary_)))


tfidfpd = tfidf_list_to_pd(tfidf_list)
sim = cosine_similarity(tfidf_list)


cosnumpd = tfidfpd_to_cosnumpd(tfidfpd)
#print(cosnumpd, sep='\t')


# In[5]:


tfpd = tfidf_list_to_pd(tf_list)
sum_column = tfpd.sum(axis=0)
df_s = sum_column.sort_values(ascending=False)
df_s_list = df_s.index.tolist()


out_ruigigo = ''
# 頻度上位20
for l in df_s_list[:40]:
    out_ruigigo += ruigigo(l)


# In[6]:


# get_html_ruigigo(ans_all)


# In[7]:


# tfidfpd


# In[8]:

# 印象属性値
df_mora_count_tmp = []
df_mora_count_song = []
lylics_ruby = list_to_ruby(lyliclist)

mora_list = getmora(lylics_ruby)
mora_list_last = getmora_last(lylics_ruby)


mora_list = getmora(lylics_ruby)
mora_list_last = getmora_last(lylics_ruby)

#count = countjapanmora(mora_list)
count = countjapanmora(mora_list + mora_list_last)


# print(CountListToDf(count))
df_mora_count_song.append(CountListToDf(count))
df_mora_count_tmp.append(CountListToDf(count))

score_index = ['キレ・俊敏さ', '柔らかさ・丸み', '躍動感', '大きさ・安定感']
score_index_title = ['キレ・俊敏さ_t', '柔らかさ・丸み_t', '躍動感_t', '大きさ・安定感_t']
# score_index_pro = ['濁音', '破裂音', '拗音', '息の入る音','ナ・マ・ヤ行']
score_index_pro = ['濁音', '破裂音', '拗音', '息の入る音', 'ナ・マ・ヤ行', 'ア段', 'イ段', 'ウ段', 'エ段', 'オ段', 'ア段ヤ行なし', 'ウ段ヤ行なし',
                   'オ段ヤ行なし']
lylics_score = calc_score(df_mora_count_tmp)
lylics_score_pro = calc_score_pro(df_mora_count_tmp)

lylics_score_df = pd.DataFrame(lylics_score, columns=score_index)
lylics_score_df2 = pd.DataFrame(lylics_score_pro, columns=score_index_pro)
lylics_score_df = pd.concat([lylics_score_df, lylics_score_df2], axis=1)


toukeiryou_df = pd.read_pickle('lylics_score_song_df_all_toukeiryou.pkl')
toukei_mean_df = toukeiryou_df[:][1:2]
toukei_std_df = toukeiryou_df[:][2:3]


tmp_df = pd.concat([lylics_score_df, toukei_mean_df, toukei_std_df]).rename(
    index={'mean': 0, 'std': 0})
# 0,1,2行目...曲の値、平均、標準偏差

hensati = (tmp_df[:][0:1] - tmp_df[:][1:2])/tmp_df[:][2:3] * 10 + 50
hensati
string_score_list = hensati.values.tolist()[0]


string_score = "["
for i in string_score_list:

    string_score += str(i) + ","
string_score += "]"


# In[9]:


out_score1 = '''    <div style="width:1470px;" >
    <canvas id="chart"></canvas>
  </div>
  <script>
    var ctx = document.getElementById("chart").getContext('2d');
    var myChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels:  ['キレ・俊敏さ', '柔らかさ・丸み', '躍動感', '大きさ・安定感','濁音', '破裂音', '拗音', '息の入る音', 'ナ・マ・ヤ行', 'ア段', 'イ段', 'ウ段', 'エ段', 'オ段', 'ア段ヤ行なし', 'ウ段ヤ行なし',
                   'オ段ヤ行なし'],  // Ｘ軸のラベル
            datasets: [
                {
                    label: "スコア",                            // 系列名
                   data:'''
out_score2 = ''',                  // ★必須　系列Ａのデータ
                    backgroundColor: "blue",
                },     
            ]
},
	options: {                       // オプション
            responsive: true,  // canvasサイズ自動設定機能を使わない。HTMLで指定したサイズに固定
            scales: {                          // 軸設定
                xAxes: [{                       // Ｘ軸設定
                }],
                yAxes: [{
                        display: true,                 // 表示の有無
                        ticks: {                       // 目盛り
                            min: 0,                        // 最小値
                            max: 100,                       // 最大値
                        },
                }],
            },
        }
    });
  
  </script>'''

out_score = out_score1 + string_score + out_score2


# In[10]:


lylics_score_df


# In[11]:


# 単語ごと
#out_word = get_html_cosnumpd_word(ans_all,tfidfpd)


# In[12]:

#out_word_all = get_html_cosnumpd_word_all(ans_all,X_all_pd_last)
out_word_all = get_html_cosnumpd_word_use_dict(ans_all, wakati)


# In[13]:


out_sentence = get_html_cosnumpd_sentence(ans_all)


# In[14]:


html_head = '''<!doctype html>

<html lang="ja">

<head>
  <!-- Required meta tags -->
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.7.2/Chart.bundle.js"></script>
  <!-- https://appsol-one.com/ui/chart-bar/ -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"
    integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">
  <!-- 本文 -->

  <link rel="stylesheet" href="result.css">
  <title>出力結果</title>
</head>

<body>
  <div class="container">
    <div class="col">
      <h1>出力結果</h1>

      <!-- タブ部分 -->
      <ul id="myTab" class="nav nav-tabs mb-3" role="tablist">
        <li class="nav-item" role="presentation">
          <button type="button" id="profile-tab" class="nav-link active" data-bs-toggle="tab" data-bs-target="#profile"
            role="tab" aria-controls="profile" aria-selected="true">サビ</button>
        </li>
        <li class="nav-item" role="presentation">
          <button type="button" id="contact-tab" class="nav-link" data-bs-toggle="tab" data-bs-target="#contact"
            role="tab" aria-controls="contact" aria-selected="false">重要語</button>
        </li>
        <li class="nav-item" role="presentation">
          <button type="button" id="ruigigo-tab" class="nav-link" data-bs-toggle="tab" data-bs-target="#ruigigo"
            role="tab" aria-controls="ruigigo" aria-selected="false">類義語</button>
        </li>
        <li class="nav-item" role="presentation">
          <button type="button" id="home-tab" class="nav-link" data-bs-toggle="tab" data-bs-target="#home"
            role="tab" aria-controls="home" aria-selected="false">印象</button>
        </li>
      </ul>

      <!-- パネル部分 -->
      <div id="myTabContent" class="tab-content">'''

html_foot = '''      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta1/dist/js/bootstrap.bundle.min.js"
    integrity="sha384-ygbV9kiqUc6oa4msXn9868pTtWMgiQaeYH7/t7LECLbyPA2x65Kgf80OJFdroafW"
    crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.5.4/dist/umd/popper.min.js"
    integrity="sha384-q2kxQ16AaE6UbzuKqyBE9/u/KzioAlnx2maXQHiDX9d4/zp8Ok3f+M7DPm+Ib6IU"
    crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta1/dist/js/bootstrap.min.js"
    integrity="sha384-pQQkAEnwaBkjpqZ8RU1fF1AKtTcHJwFl3pblpTlHXybJjHpMYo79HY3hIi4NKxyj"
    crossorigin="anonymous"></script>
</body>

</html>'''

html_sec = []
html_sec.append(
    '<div id="profile" class="tab-pane active" role="tabpanel" aria-labelledby="profile-tab">')
html_sec.append(
    '<div id="contact" class="tab-pane" role="tabpanel" aria-labelledby="contact-tab">')
html_sec.append(
    '<div id="ruigigo" class="tab-pane" role="tabpanel" aria-labelledby="ruigigo-tab">')
html_sec.append(
    '<div id="home" class="tab-pane" role="tabpanel" aria-labelledby="home-tab">')
html_sec_foot = '</div>'


# In[15]:


f = open('output.html', 'w', encoding='utf-8')

#html_str = [out_sentence,out_word,out_ruigigo,out_score]
html_str = [out_sentence, out_word_all, out_ruigigo, out_score]

html_out = html_head
i = 0
for se in html_sec:
    html_out += se
    html_out += html_str[i]
    html_out += html_sec_foot
    i += 1
html_out += html_foot

f.write(html_out)

f.close()


# In[16]:


subprocess.Popen(['start', 'output.html'], shell=True)
