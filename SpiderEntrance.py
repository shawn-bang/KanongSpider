# -*- coding:utf-8 -*-
import os, sys, re, time, json, requests, random, base64, datetime, hashlib, logging

from HTMLParser import HTMLParser

from elasticsearch import Elasticsearch

from lxml import etree

from lxml.html import fromstring, tostring

from StringIO import StringIO

from PIL import Image

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

        self.html_path = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/html"
        self.images_path = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/images"
        self.videos_path = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/videos"
        self.html_template_path = "http://127.0.0.1:8008/template/KanongTemplate.html"
        self.qrcode_image_save_path = "/Users/shawnxiao/Desktop/kanong_qrcode.png"

        self.username = username_input
        self.password = password_input

        self.website_hostname = "https://www.51kanong.com/"
        self.loginUrl = "https://www.51kanong.com/member.php?mod=logging&action=login"
        self.homepageUrl = "https://www.51kanong.com/portal.php"
        self.getQRCodeUrl = "https://www.51kanong.com/plugin.php?id=zimucms_appscan&model=pcqrcode&infloat=yes&handlekey=pcqrcode&inajax=1&ajaxtarget=fwin_content_pcqrcode"

        self.HTMLParser = HTMLParser()
        self.es = Elasticsearch([{'host': ip, 'port': port}])

        self.crawlTargetUrls = {
            "dk_kz": "https://www.51kanong.com/yh-119-@.htm",  # ——贷款口子分类——贷款口子
            "xyk_kz": "https://www.51kanong.com/yh-118-@.htm",  # ——信用卡分类——信用卡口子
            "zhyp_spjc": "https://www.51kanong.com/yh-129-@.htm",  # ——综合音频教程——分类
            "zjpx": "https://www.51kanong.com/yh-120-@.htm",  # ——综合音频教程——中介培训
            "xykjl": "https://www.51kanong.com/yh-209-@.htm",  # ——讨论口子——信用卡交流
            "rmjl": "https://www.51kanong.com/yh-140-@.htm"  # ——查询助手——热门交流&贷款口子交流
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

        md5 = hashlib.md5()
        md5.update(self.password.encode())
        password_md5 = md5.hexdigest()

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


    def crawlObjectViedo(self):
        video_res = self.session.get("https://webcast.vyuan8.cn/vyuan/plugin.php?id=vyuan_zhibo&mod=viewpc&identify=5712929&password=zxjd123")
        video_page = video_res.content
        video_page_doc = etree.HTML(video_page)
        regex1 = r'var videoUrl="(.*?)"'
        m3u8_url = self.regexSearch(regex1, video_page, 1)
        print m3u8_url

        regex2 = r'http\:\/\/(.*?)\/'
        m3u8_url_host = self.regexSearch(regex2, m3u8_url, 0)
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
            file_name = "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/" + ts_file_names[i] + ".mp4"
            command = "cd " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/ " + "&&" + " touch " + ts_file_names[i] + ".mp4"
            if os.system(command) == 0:
                with open(file_name, "wb") as code:
                    code.write(ts_request_res.content)

        command1 = "cd " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/ " + "&&" + " touch test.mp4"
        if os.system(command1) == 0:
            for i in range(len(ts_file_names)):
                command2 = "cat " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/" + ts_file_names[i] + ".mp4 >> " + "/Users/shawnxiao/Workspace/SpiderWorkspace/kanong/temp/test.mp4"
                if os.system(command2) == 0:
                    print "successful......."
                else:
                    print "fail......"

    def main(self):
        # login_status = self.login_by_username()
        if True:
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

                for i in range(len(list_table_tbodys)):
                    tbody = etree.HTML(etree.tostring(list_table_tbodys[i]))
                    article_a = tbody.xpath("//a[@class='deanforumtitname']")[0]
                    article_page_url = article_a.attrib['href']
                    article_title = article_a.text.encode("ISO-8859-1").decode("utf-8")
                    logger.info(article_page_url)
                    logger.info(article_title)

                pager_title = list_page_doc.xpath("//div[@class='pg']//input[@name='custompage']/following-sibling::span/@title")[0]
                total_page_count = ''.join(re.findall(r"\d+\.?\d*", pager_title))
                logger.info(total_page_count)

                for n in range(2, int(total_page_count)):
                    list_next_page_url = v.replace("@", str(n))
                    list_next_page_res = self.session.get(list_next_page_url)
                    list_next_page_doc = etree.HTML(list_next_page_res.content)
                    next_page_tbodys = list_next_page_doc.xpath("//table[@id='threadlisttableid']/tbody[starts-with(@id, 'normalthread')]")

                    for i in range(len(next_page_tbodys)):
                        tbody = etree.HTML(etree.tostring(next_page_tbodys[i]))
                        article_a = tbody.xpath("//a[@class='deanforumtitname']")[0]
                        article_page_url = article_a.attrib['href']
                        article_title = article_a.text.encode("ISO-8859-1").decode("utf-8")
                        logger.info(article_page_url)
                        logger.info(article_title)

        else:
            sys.exit(1)

        self.crawlObjectViedo()


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
