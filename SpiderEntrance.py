# -*- coding:utf-8 -*-
import os, re, time, json, requests, random, base64, datetime, hashlib, logging

from HTMLParser import HTMLParser

from elasticsearch import Elasticsearch

from lxml import etree

from lxml.html import fromstring, tostring

from StringIO import StringIO

from PIL import Image

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

ip = "0.0.0.0"
port = "9201"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 创建 handler 输出到文件
handler = logging.FileHandler("kanong-spider.log", mode='w')
handler.setLevel(logging.INFO)

# handler 输出到控制台
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# 创建 logging format
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
ch.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)
logger.addHandler(ch)


class KanongSpider(object):

    def __init__(self, username_input, password_input):

        self.session = requests.session()

        self.source_hostname = "http://127.0.0.1:8008/"
        self.html_path = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/html/"
        self.html_source_url = self.source_hostname + "html/"
        self.images_path = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/images/"
        self.images_source_url = self.source_hostname + "images/"
        self.videos_path = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/videos/"
        self.videos_source_url = self.source_hostname + "videos/"
        self.html_template_url = "http://127.0.0.1:8008/template/KanongTemplate.html"
        self.qrcode_image_save_path = "/Users/shawnxiao/Desktop/kanong_qrcode.png"

        self.html_template = requests.get(self.html_template_url).content
        self.html_template_title_html_pattern = "#article_title_html#"
        self.html_template_article_html_pattern = "#article_content_html#"
        self.html_template_title_pattern = "#article_title#"

        self.username = username_input
        self.password = password_input

        self.website_hostname = "https://www.51kanong.com/"
        self.loginUrl = "https://www.51kanong.com/member.php?mod=logging&action=login"
        self.homepageUrl = "https://www.51kanong.com/portal.php"
        self.getQRCodeUrl = "https://www.51kanong.com/plugin.php?id=zimucms_appscan&model=pcqrcode&infloat=yes&handlekey=pcqrcode&inajax=1&ajaxtarget=fwin_content_pcqrcode"

        self.HTMLParser = HTMLParser()
        self.es_index = "spider"
        self.es_index_type = "kanong"
        self.es = Elasticsearch([{'host': ip, 'port': port}])

        self.crawlTargetUrls = {
            # "dk_kz": "https://www.51kanong.com/yh-119-@.htm",  # ——贷款口子分类——贷款口子
            # "xyk_kz": "https://www.51kanong.com/yh-118-@.htm",  # ——信用卡分类——信用卡口子
            "zhyp_spjc": "https://www.51kanong.com/yh-129-@.htm"  # ——综合音频教程——分类
            # "zjpx": "https://www.51kanong.com/yh-120-@.htm",  # ——综合音频教程——中介培训
            # "xykjl": "https://www.51kanong.com/yh-209-@.htm",  # ——讨论口子——信用卡交流
            # "rmjl": "https://www.51kanong.com/yh-140-@.htm"  # ——查询助手——热门交流&贷款口子交流
        }

    def login_by_scan(self):
        self.session.get(self.homepageUrl)
        self.session.get(self.loginUrl)
        get_qrcode_res = self.session.get(self.getQRCodeUrl)

        code_page_content_doc = etree.HTML(get_qrcode_res.content)
        code_img_element = code_page_content_doc.xpath("//img[@id='qr-img']")
        query_qrcode_url = code_img_element[0].attrib['src']
        query_qrcode_url = 'https://www.51kanong.com/' + query_qrcode_url

        regex1 = r"document\.getElementById\('checkhashpcurl'\)\.value = '(.*?)';"
        pattern = re.compile(regex1)
        matcher = re.search(pattern, get_qrcode_res.content)
        check_scan_status_url = matcher.group(1)
        check_scan_status_url = 'https://www.51kanong.com/' + check_scan_status_url

        time_string = check_scan_status_url[-10::]

        self.session.cookies.set('kanong_6ab6_sendmail', '1')
        self.session.cookies.set('Hm_lvt_9b95fb0ffb849e12ddf8136e9082a3fc', time_string)
        self.session.cookies.set('Hm_lpvt_9b95fb0ffb849e12ddf8136e9082a3fc', time_string)

        query_qrcode_res = self.session.get(query_qrcode_url)
        query_qrcode_string = StringIO(query_qrcode_res.content)
        qrcode_image = Image.open(query_qrcode_string)
        qrcode_image.save(self.qrcode_image_save_path)

        flag = False
        # 循环就是重复执行循环体里面的代码
        while flag == False:
            time.sleep(3)
            status_code_res = self.session.get(check_scan_status_url)
            status_code = status_code_res.content
            print status_code
            if status_code == '202':
                flag = True
                login_status = False
                while not login_status:
                    time.sleep(2)
                    status_code_res = self.session.get(check_scan_status_url)
                    status_code = status_code_res.content
                    print status_code
                    if status_code == '200':
                        login_status = True
                        login_result_res = self.session.get(self.loginUrl)
                        print login_result_res.content

    def login_by_username(self):
        login_page_res = self.session.get(self.loginUrl)
        login_page_doc = etree.HTML(login_page_res.content)
        logging_url = login_page_doc.xpath("//form[@name='login']")[0].attrib['action']
        logging_url = self.website_hostname + logging_url
        form_hash = login_page_doc.xpath("//input[@name='formhash']")[0].attrib['value']

        password_md5 = KanongSpider.md5(self.password)

        login_data = {
            "loginsubmit": "yes",
            "inajax": "1",
            "formhash": form_hash,
            "referer": self.homepageUrl,
            "username": self.username,
            "password": password_md5,
            "questionid": "0"
        }

        logging_res = self.session.post(logging_url, data=login_data)
        logging_status = logging_res.content.find(self.username)
        if logging_status > 0:
            logger.info(self.username + " : login success!")
            return True
        else:
            logger.info(self.username + " : login fail!")
            logger.info("Error message : " + logging_res.content)
            return False

    def crawlTargetPage(self):
        # TODO
        print "pending......"

    def regexSearch(self, regex, content, index):
        pattern = re.compile(regex)
        matcher = re.search(pattern, content)
        result = matcher.group(index)
        return result

    def crawl_object_viedo(self, article_content_doc):
        # 直接在文章主体中嵌入video标签，直接下载-------------------------------------------------------------------------------
        article_content_inner_videos = article_content_doc.xpath("//table//div[@class='t_fsz']//video")
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
            file_name = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/videos/" + KanongSpider.md5(video_url) + file_format
            command = "cd " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/videos/ " + "&&" + " touch " + KanongSpider.md5(video_url) + file_format
            if os.system(command) == 0:
                with open(file_name, "wb") as code:
                    code.write(video_request_res.content)

            video_element.set("poster", "")
            video_inner_source_element.set("src", self.videos_source_url + KanongSpider.md5(video_url) + file_format)

        # 文章主体链接中嵌入视频播放链接，特征http://webcast.vyuan8.cn----------------------------------------------------------
        article_content_inner_videos1 = article_content_doc.xpath("//table//div[@class='t_fsz']//a[starts-with(@href, 'http://webcast.vyuan8.cn')]")
        for x in range(len(article_content_inner_videos1)):
            print ">>>>>>>>>222222"
            show_video_url = article_content_inner_videos1[x].attrib['href']
            show_video_res = self.session.get(show_video_url)

            regex1 = r'var videoUrl="(.*?)"'
            results1 = re.findall(regex1, show_video_res.content)
            video_url = results1[0]

            print "!!!!!!video_url: " + video_url

            regex2 = r'\/(.*?)\.([\w]+)'
            results2 = re.findall(regex2, video_url)
            content_parts = results2[len(results2) - 1]
            file_format = "." + content_parts[len(content_parts) - 1]
            video_file_name = KanongSpider.md5(video_url) + file_format

            video_request_res = requests.session().get(video_url)
            file_name = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/videos/" + video_file_name
            command = "cd " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/videos/ " + "&&" + " touch " + video_file_name
            if os.system(command) == 0:
                with open(file_name, "wb") as code:
                    code.write(video_request_res.content)

            video_inner_source_element_string = '<video autoplay="autoplay" src="' + self.videos_source_url + video_file_name + '" style="width: 896px; height: 506px;"></video>'
            video_inner_source_element = etree.fromstring(video_inner_source_element_string)
            article_content_inner_videos1[x].getparent().replace(article_content_inner_videos1[x], video_inner_source_element)

        # 其它情况没有非常强的结构逻辑，不能标准化爬取，再想办法
        article_content_inner_password = article_content_doc.xpath(
            u"//div[@class='viewbox firstfloor cl']//table//div[@class='t_fsz']//font[contains(text(), '密码')]")
        article_content_inner_videos2 = article_content_doc.xpath("//table//div[@class='t_fsz']//a[starts-with(@href, 'https://www.vyuan8.com/vyuan/plugin.php')]")
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

                entrance_video_res = self.session.get(entrance_video_url)
                if "btnInputPwd" in entrance_video_res.content:
                    print "password error!!!!!!"
                else:
                    print "password correct!!!!!!"
                    regex1 = r'var videoUrl="(.*?)"'
                    m3u8_url = KanongSpider.regexSearch(regex1, entrance_video_res.content, 1)
                    print m3u8_url

                    if ".m3u8" in m3u8_url:
                        print "完整视频"
                    else:
                        print "试看视频"
                        continue

                    regex2 = r'http\:\/\/(.*?)\/'
                    m3u8_url_host = KanongSpider.regexSearch(regex2, m3u8_url, 0)
                    print m3u8_url_host

                    m3u8_res = self.session.get(m3u8_url)

                    regex3 = r'record\/.*?\.ts'
                    results_ts = re.findall(regex3, m3u8_res.content)
                    print results_ts

                    regex4 = r'_(.*?)\.ts'
                    ts_file_names = re.findall(regex4, m3u8_res.content)
                    print ts_file_names

                    for i in range(len(results_ts)):
                        ts_request_url = m3u8_url_host + results_ts[i]
                        print ts_request_url
                        ts_request_res = self.session.get(ts_request_url)
                        file_name = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/" + ts_file_names[
                            i] + ".mp4"
                        command = "cd " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/ " + "&&" + " touch " + \
                                  ts_file_names[i] + ".mp4"
                        if os.system(command) == 0:
                            with open(file_name, "wb") as code:
                                code.write(ts_request_res.content)

                    video_file_name = KanongSpider.md5(entrance_video_url) + ".mp4"
                    command1 = "cd " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/ " + "&&" + " touch " + video_file_name
                    if os.system(command1) == 0:
                        for i in range(len(ts_file_names)):
                            command2 = "cat " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/" + \
                                       ts_file_names[
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

                video_inner_source_element_string = '<video autoplay="autoplay" src="' + self.videos_source_url + video_file_name + '" style="width: 896px; height: 506px;"></video>'
                video_inner_source_element = etree.fromstring(video_inner_source_element_string)
                a_element.getparent().replace(a_element, video_inner_source_element)

        # 替换文章中引用的其它文章链接
        article_content_inner_a = article_content_doc.xpath("//table//div[@class='t_fsz']//font[starts-with(text(), 'https://www.51kanong.com/')]")
        for x in range(len(article_content_inner_a)):
            print ">>>>>>>>>444444"
            font_element = article_content_inner_a[x]
            font_parent = font_element.getparent()
            html_source_url_full = self.html_source_url + KanongSpider.md5(font_element.text) + ".html"
            font_element.text = html_source_url_full
            font_parent.set("href", html_source_url_full)

    # md5字符串
    @staticmethod
    def md5(content):
        md5 = hashlib.md5()
        md5.update(content.encode())
        result = md5.hexdigest()
        return result

    # 爬取文章中嵌入的图片信息
    def crawl_article_inner_images(self, article_content_doc):
        article_content_inner_images = article_content_doc.xpath("//table//div[@class='t_fsz']//img[@file]")
        for x in range(len(article_content_inner_images)):
            img_url = article_content_inner_images[x].attrib['file']

            # 设置图片默认宽高
            try:
                img_width = article_content_inner_images[x].attrib['width']
                img_height = article_content_inner_images[x].attrib['height']
            except KeyError:
                img_width = "400"
                img_height = "711"

            img_res = requests.session().get(img_url)
            img_string = StringIO(img_res.content)
            img_stream = Image.open(img_string)
            img_format = img_stream.format
            img_size = img_stream.size

            # 如果图片是表情图片，大小需要给定真实图片大小，否则表情图片会被撑的很大，很难看
            img_width_real = img_size[0]
            img_height_real = img_size[1]
            if img_width_real < 400:
                img_width = str(img_width_real)
                img_height = str(img_height_real)

            img_filename = KanongSpider.md5(img_url) + "." + img_format
            new_img_url = self.images_source_url + img_filename
            img_stream.save(self.images_path + img_filename)

            new_img_element_string = "<img id='" + KanongSpider.md5(
                img_url) + "' src='" + new_img_url + "' width='" + img_width + "' height='" + img_height + "'/>"
            new_img_element = etree.fromstring(new_img_element_string)

            article_content_inner_images[x].getparent().replace(article_content_inner_images[x], new_img_element)

    # 爬去其它列表页文章目标地址和相关概要信息 & 爬去列表页文章内容
    def crawl_article_page(self, crawl_root_link, tbodys):
        for i in range(len(tbodys)):
            article_id = ''.join(re.findall(r"\d+\.?\d*", tbodys[i].attrib['id']))
            tbody = etree.HTML(etree.tostring(tbodys[i]))
            article_a = tbody.xpath("//a[@class='deanforumtitname']")[0]
            article_page_url = article_a.attrib['href']
            article_page_url = self.website_hostname + article_page_url
            logger.info("!!!!!!article_page_url : " + article_page_url)
            article_title = article_a.text
            # 爬取文章页面详细内容
            article_page_res = self.session.get(article_page_url)
            article_page_doc = etree.HTML(article_page_res.content.replace("&nbsp;", " "))

            # 爬取文章标题html
            title_element = article_page_doc.xpath("//div[@class='deanviewtit cl']")[0]
            title_html = etree.tostring(title_element)
            title_html = self.HTMLParser.unescape(title_html)

            # 爬取文章标签分类信息
            type_element = article_page_doc.xpath("//span[@id='thread_subject']/preceding-sibling::a")
            article_type = None
            if type_element:
                article_type = type_element[0].text
                article_type = article_type.replace("[", "").replace("]", "")

            # 爬取文章详细内容html
            article_content_element = article_page_doc.xpath("//div[@class='viewbox firstfloor cl']/table")[0]
            article_content_html = etree.tostring(article_content_element)
            article_content_doc = etree.HTML(article_content_html)

            # 解析文章详细内容 & 爬取文章中嵌入的图片信息
            self.crawl_article_inner_images(article_content_doc)

            # 解析文章详细内容 & 爬取视频
            self.crawl_object_viedo(article_content_doc)

            new_article_content_html = etree.tostring(article_content_doc)
            new_article_content_html = self.HTMLParser.unescape(new_article_content_html)

            article_content = article_page_doc.xpath("//div[@class='viewbox firstfloor cl']//div[@class='t_fsz']//table//text()")
            article_content = ''.join(article_content)
            # 处理特殊字符
            article_content = article_content.replace(' ', '').replace('\n', '').replace('\r', '')
            article_content = article_content
            pattern = re.compile(ur"[\u4e00-\u9fa5]")
            article_content = "".join(pattern.findall(article_content.decode('utf8'))).encode('utf-8')

            new_article_content_html = self.html_template.replace(self.html_template_title_pattern, article_title).\
                replace(self.html_template_title_html_pattern, title_html).\
                replace(self.html_template_article_html_pattern, new_article_content_html)

            file_name = article_id + ".html"
            file_full_path = self.html_path + file_name
            command = "cd " + self.html_path + "&&" + " touch " + article_id + ".html"
            if os.system(command) == 0:
                with open(file_full_path, "wb") as html:
                    html.write(new_article_content_html)
                logger.info("Save Html success! FileName is " + file_full_path)
            else:
                logger.info("Save Html fail! FileName is " + file_full_path)

            article_body = {
                "crawl_root_link": crawl_root_link,
                "title": article_title,
                "date": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                "article": article_content,
                "link": self.html_source_url + file_name,
                "source_link": article_page_url,
                "type": article_type
            }
            create_status = self.es.index(index=self.es_index, doc_type=self.es_index_type, id=article_id,
                                          body=article_body)
            if not create_status:
                logger.info("Crawl Fail! URL: " + article_page_url)

    def main(self):
        start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        login_status = self.login_by_username()
        if login_status:
            # 爬取目标地址列表页首页内容
            for k in self.crawlTargetUrls:
                v = self.crawlTargetUrls.get(k)
                logger.info("-------------------------------crawl start-------------------------------")
                logger.info(v)
                logger.info("-------------------------------------------------------------------------")
                list_page_url = v.replace("@", "1")
                # 控制页面的显示模式为列表模式
                self.session.cookies.set("kanong_6ab6_forumdefstyle", "1")
                list_page_res = self.session.get(list_page_url)
                list_page_doc = etree.HTML(list_page_res.content)
                list_table_tbodys = list_page_doc.xpath("//table[@id='threadlisttableid']/tbody[starts-with(@id, 'normalthread')]")

                # 爬取列表页首页文章目标地址和相关概要信息
                self.crawl_article_page(v, list_table_tbodys)

                # 爬取总页数
                pager_title = list_page_doc.xpath("//div[@class='pg']//input[@name='custompage']/following-sibling::span/@title")[0]
                total_page_count = ''.join(re.findall(r"\d+\.?\d*", pager_title))
                logger.info(total_page_count)

                # 爬去其它全部列表页内容
                for n in range(2, int(total_page_count)):
                    list_next_page_url = v.replace("@", str(n))
                    list_next_page_res = self.session.get(list_next_page_url)
                    list_next_page_doc = etree.HTML(list_next_page_res.content)
                    next_page_tbodys = list_next_page_doc.xpath("//table[@id='threadlisttableid']/tbody[starts-with(@id, 'normalthread') or starts-with(@id, 'stickthread')]")

                    # 爬取其它列表页文章目标地址和相关概要信息 & 爬去列表页文章内容
                    self.crawl_article_page(v, next_page_tbodys)
        end_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        logger.info("Runtime: from " + start_time + " to " + end_time)

        # self.crawl_object_viedo()

        # --------------------------------------------------------------------------------------------------------------
        # test_page_res = self.session.get("https://www.51kanong.com/xyk-2172281-1.htm")
        #
        # print test_page_res.content
        #
        # test_page_doc = etree.HTML(test_page_res.content)
        # title = test_page_doc.xpath("//span[@id='thread_subject']/text()")[0]
        #
        # # print title
        #
        # article_content_element = test_page_doc.xpath("//div[contains(@class, 'firstfloor')]//div[@class='t_fsz']/table")[0]
        # article_content = etree.tostring(article_content_element)
        # article_content = self.HTMLParser.unescape(article_content)
        #
        # # print article_content
        #
        # create_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
        #
        # create_status = self.es.index(index="kanong", doc_type="article", id=1, body={"title": title, "inner_html": article_content, "create_time": create_time})
        #
        # print create_status

        # crawling ......
        # TODO


username = raw_input('Please input username: ')
password = raw_input('Please input password: ')
KanongSpider(username, password).main()
