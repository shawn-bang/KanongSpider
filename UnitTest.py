# -*- coding:utf-8 -*-
import os, sys, re, time, json, requests, random, base64, datetime, hashlib

from lxml import etree

from StringIO import StringIO

from PIL import Image

sys

# print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
#
# f = open("/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/html/2186223.html")
# f_content = f.read()
# f.close()

# print f_content

session = requests.session()

loginUrl = "https://www.51kanong.com/member.php?mod=logging&action=login"
website_hostname = "https://www.51kanong.com/"
homepageUrl = "https://www.51kanong.com/portal.php"
videos_source_url = "http://127.0.0.1:8008/videos/"
html_source_url = "http://127.0.0.1:8008/html/"


def login_by_username(username_input, password_input):
    login_page_res = session.get(loginUrl)
    login_page_doc = etree.HTML(login_page_res.content)
    logging_url = login_page_doc.xpath("//form[@name='login']")[0].attrib['action']
    logging_url = website_hostname + logging_url
    form_hash = login_page_doc.xpath("//input[@name='formhash']")[0].attrib['value']

    password_md5 = md5(password_input)

    login_data = {
        "loginsubmit": "yes",
        "inajax": "1",
        "formhash": form_hash,
        "referer": homepageUrl,
        "username": username_input,
        "password": password_md5,
        "questionid": "0"
    }

    logging_res = session.post(logging_url, data=login_data)
    logging_status = logging_res.content.find(username_input)
    if logging_status > 0:
        print username_input + " : login success!"
        return True
    else:
        print username_input + " : login fail!"
        print "Error message : " + logging_res.content
        return False


# md5字符串
def md5(content):
    md5 = hashlib.md5()
    md5.update(content.encode("utf-8"))
    result = md5.hexdigest()
    return result


def regexSearch(regex, content, index):
    pattern = re.compile(regex)
    matcher = re.search(pattern, content)
    result = matcher.group(index)
    return result


username = raw_input('Please input username: ')
password = raw_input('Please input password: ')
if login_by_username(username, password):
    # target_url = "https://www.51kanong.com/xyk-2250277-1.htm"
    # target_url = "https://www.51kanong.com/xyk-2176082-1.htm"
    target_url = "https://www.51kanong.com/xyk-1971390-1.htm"
    target_res = session.get(target_url)
    article_content_doc = etree.HTML(target_res.content)
    # 直接在文章主体中嵌入video标签，直接下载-------------------------------------------------------------------------------
    article_content_inner_videos = article_content_doc.xpath("//div[@class='viewbox firstfloor cl']//table//div[@class='t_fsz']//video")
    for x in range(len(article_content_inner_videos)):
        print ">>>>>>>>>111111"
        video_element = article_content_inner_videos[x]
        video_inner_source_element = article_content_inner_videos[x].getchildren()[0]
        video_url = video_inner_source_element.attrib['src']
        # video_url = article_content_inner_video_urls[x].attrib['src']
        print "!!!!!!video_url: " + video_url

        regex3 = r'[^/]+(?!.*.)'
        results = re.findall(regex3, video_url)
        file_name = results[0]

        regex4 = r'(?<=.)([\w]+)'
        results1 = re.findall(regex4, file_name)

        file_format = "." + results1[len(results1) - 1]

        print file_format

        video_request_res = requests.session().get(video_url)
        file_name = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/videos/" + md5(video_url) + file_format
        command = "cd " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/videos/ " + "&&" + " touch " + md5(video_url) + file_format
        if os.system(command) == 0:
            with open(file_name, "wb") as code:
                code.write(video_request_res.content)

        video_element.set("poster", "")
        video_inner_source_element.set("src", videos_source_url + md5(video_url) + file_format)

    # 文章主体链接中嵌入视频播放链接，特征http://webcast.vyuan8.cn----------------------------------------------------------
    article_content_inner_videos1 = article_content_doc.xpath("//div[@class='viewbox firstfloor cl']//table//div[@class='t_fsz']//a[starts-with(@href, 'http://webcast.vyuan8.cn')]")
    for x in range(len(article_content_inner_videos1)):
        print ">>>>>>>>>222222"
        show_video_url = article_content_inner_videos1[x].attrib['href']
        show_video_res = session.get(show_video_url)

        regex1 = r'var videoUrl="(.*?)"'
        results1 = re.findall(regex1, show_video_res.content)
        video_url = results1[0]

        print "!!!!!!video_url: " + video_url

        regex2 = r'\/(.*?)\.([\w]+)'
        results2 = re.findall(regex2, video_url)
        content_parts = results2[len(results2) - 1]
        file_format = "." + content_parts[len(content_parts) - 1]
        video_file_name = md5(video_url) + file_format

        video_request_res = requests.session().get(video_url)
        file_name = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/videos/" + video_file_name
        command = "cd " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/videos/ " + "&&" + " touch " + video_file_name
        if os.system(command) == 0:
            with open(file_name, "wb") as code:
                code.write(video_request_res.content)

        video_inner_source_element_string = '<video autoplay="autoplay" src="' + videos_source_url + video_file_name + '" style="width: 896px; height: 506px;"></video>'
        video_inner_source_element = etree.fromstring(video_inner_source_element_string)
        article_content_inner_videos1[x].getparent().replace(article_content_inner_videos1[x], video_inner_source_element)

    # 其它情况没有非常强的结构逻辑，不能标准化爬取，再想办法
    article_content_inner_password = article_content_doc.xpath(u"//div[@class='viewbox firstfloor cl']//table//div[@class='t_fsz']//font[contains(text(), '密码')]")
    article_content_inner_videos2 = article_content_doc.xpath("//div[@class='viewbox firstfloor cl']//table//div[@class='t_fsz']//a[starts-with(@href, 'https://www.vyuan8.com/vyuan/plugin.php')]")
    for x in range(len(article_content_inner_password)):
        print ">>>>>>>>>333333"
        font_password_element = article_content_inner_password[x]
        font_text = font_password_element.text
        password = ''.join(re.findall(r"\d", font_text))
        for z in range(len(article_content_inner_videos2)):
            a_element = article_content_inner_videos2[z]
            entrance_video_url = a_element.attrib['href']
            print "Replace Before:" + entrance_video_url
            entrance_video_url = entrance_video_url.replace("https://www.vyuan8.com", "https://webcast.vyuan8.cn").replace("activity_id", "identify").replace("mod=introduceV", "mod=viewpc")
            entrance_video_url = entrance_video_url + "&password=" + password
            print "Replace After:" + entrance_video_url

            entrance_video_res = session.get(entrance_video_url)
            if "btnInputPwd" in entrance_video_res.content:
                print "password error!!!!!!"
            else:
                print "password correct!!!!!!"
                video_page_doc = etree.HTML(entrance_video_res.content)
                regex1 = r'var videoUrl="(.*?)"'
                m3u8_url = regexSearch(regex1, entrance_video_res.content, 1)
                print m3u8_url

                if ".m3u8" in m3u8_url:
                    print "完整视频"
                else:
                    print "试看视频"
                    continue

                regex2 = r'http\:\/\/(.*?)\/'
                m3u8_url_host = regexSearch(regex2, m3u8_url, 0)
                print m3u8_url_host

                m3u8_res = session.get(m3u8_url)

                regex3 = r'record\/.*?\.ts'
                results_ts = re.findall(regex3, m3u8_res.content)
                print results_ts

                regex4 = r'_(.*?)\.ts'
                ts_file_names = re.findall(regex4, m3u8_res.content)
                print ts_file_names

                for i in range(len(results_ts)):
                    ts_request_url = m3u8_url_host + results_ts[i]
                    print ts_request_url
                    ts_request_res = session.get(ts_request_url)
                    file_name = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/" + ts_file_names[i] + ".mp4"
                    command = "cd " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/ " + "&&" + " touch " + \
                              ts_file_names[i] + ".mp4"
                    if os.system(command) == 0:
                        with open(file_name, "wb") as code:
                            code.write(ts_request_res.content)

                video_file_name = md5(entrance_video_url) + ".mp4"
                command1 = "cd " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/ " + "&&" + " touch " + video_file_name
                if os.system(command1) == 0:
                    for i in range(len(ts_file_names)):
                        command2 = "cat " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/" + ts_file_names[
                            i] + ".mp4 >> " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/" + video_file_name
                        if os.system(command2) == 0:
                            print "cat successful......."
                        else:
                            print "cat fail......"
                    command3 = "mv /Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/" + video_file_name + " /Users/shawnxiao/Workspace/SpiderWorkspace/kanong/videos && rm -f /Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/*.mp4"
                    if os.system(command3) == 0:
                        print "mv successful"
                    else:
                        print "mv fail......"

            video_inner_source_element_string = '<video autoplay="autoplay" src="' + videos_source_url + video_file_name + '" style="width: 896px; height: 506px;"></video>'
            video_inner_source_element = etree.fromstring(video_inner_source_element_string)
            a_element.getparent().replace(a_element, video_inner_source_element)


    # 替换文章中引用的其它文章链接
    article_content_inner_a = article_content_doc.xpath("//div[@class='viewbox firstfloor cl']//table//div[@class='t_fsz']//font[starts-with(text(), 'https://www.51kanong.com/')]")
    for x in range(len(article_content_inner_a)):
        print ">>>>>>>>>444444"
        font_element = article_content_inner_a[x]
        font_parent = font_element.getparent()
        html_source_url_full = html_source_url + md5(font_element.text) + ".html"
        font_element.text = html_source_url_full
        font_parent.set("href", html_source_url_full)

    new_article_content = etree.tostring(article_content_doc)
    print new_article_content

    # img_res = requests.session().get(img_url)
    # img_string = StringIO(img_res.content)
    # img_stream = Image.open(img_string)
    # img_format = img_stream.format
    # img_size = img_stream.size
    # img_filename = md5(img_url) + "." + img_format
    # new_img_url = "http://127.0.0.1:8008/images/" + img_filename
    # img_stream.save("/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/images/" + img_filename)
    #
    # new_img_element_string = "<img id='" + md5(img_url) + "' src='" + new_img_url + "'/>"
    # new_img_element = etree.fromstring(new_img_element_string)
    #
    # article_content_inner_images[x].getparent().replace(article_content_inner_images[x], new_img_element)

# new_article_content = etree.tostring(article_content_doc)

# print new_article_content

# print html.replace("@", "1")
#
# print sys.getdefaultencoding()
#
# test_string = "注册帐号，您需要登录才可以下载或查看，没有帐号？注册个账号x仙女座安卓链接已找到��在道搜索仙女座��会出来一个图标��点进去里面有个二维码��截屏��自己在浏览器里面扫二维码就好了��不要谢我��下款打赏一下就好来自安卓APP客户端"
# pattern = re.compile(ur"[\u4e00-\u9fa5]")
# print "".join(pattern.findall(test_string.decode('utf8'))).encode('utf-8')

# img_url = "https://app-att.kanongyun.com/pic/20190420/1555736490183358_820.jpg?x-oss-process=image/watermark,image_cGljLzIwMTgwMjAzL29zc18xNTE3NjI1NjIzMDE5XzIzM182OTJfNzUzLnBuZw==,t_50,g_se,x_20,y_20"
#
# md5 = hashlib.md5()
# md5.update(img_url)
# password_md5 = md5.hexdigest()
#
# print password_md5

# query_qrcode_res = requests.session().get(img_url)
# query_qrcode_string = StringIO(query_qrcode_res.content)
# qrcode_image = Image.open(query_qrcode_string)
# print qrcode_image.size
# print qrcode_image.format
# print qrcode_image.filename
# qrcode_image.save("/Users/shawnxiao/Desktop/kanong_qrcode." + qrcode_image.format)
