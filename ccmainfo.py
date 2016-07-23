#!/usr/bin/python
import argparse
import bs4
import json
import logging
import requests
import re
import sys

TMP_FILE = 'ccmainfo.json'

TITLE = "Títol"
INFO_LINK = "Info"
HQ_VIDEO = "HQ"
MQ_VIDEO = "MQ"
SUBTITLE_1 = "Subs1"
SUBTITLE_2 = "Subs2"


name_urlbase = "http://www.tv3.cat/pvideo/FLV_bbd_dadesItem_MP4.jsp?idint="
hq_urlbase = "http://www.tv3.cat/pvideo/FLV_bbd_media.jsp?QUALITY=H&PROFILE=IPTV&FORMAT=MP4GES&ID="
subs1_urlbase = "http://dinamics.ccma.cat/pvideo/media.jsp?media=video&version=0s&profile=tv&idint="
subs2_urlbase = "http://www.tv3.cat/p3ac/p3acOpcions.jsp?idint="


###########
# Logging
logger = logging.getLogger('ccmainfo_main')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARNING)
# end internal config
############
capis = []


def cli_parse():
    parser = argparse.ArgumentParser(description='CCMA.cat INFO')
    parser.add_argument('--batch', dest='batch', nargs='?', default=False,
                        help='Run without asking for url')
    parser.add_argument('--debug', dest='verbose', action='store_true',
                        help='Debug mode')
    parser.set_defaults(verbose=False)
    args = parser.parse_args()
    return args


def get_url(args):
    if not args.batch:
        url = input("Write your URL: ")
    else:
        url = args.batch
    return url


def load_json():
    try:
        json_file = open(TMP_FILE, "r").read()
        j = json.loads(json_file)
        logger.info("Using old temporary list")
    except:
        logger.info("Creating new temporary list")
        j = []
    return j


def create_json(jin):
    j = json.loads(json.dumps(jin))
    logger.info("Rewriting temporary list")
    try:
        with open(TMP_FILE, 'w') as outfile:
            json.dump(j, outfile)
        logger.debug("Done rewriting temporary list")
    except:
        logger.error("Failed to write the temporary list.")
        sys.exit(1)


def remove_invalid_win_chars(value, deletechars):
    for c in deletechars:
        value = value.replace(c, '')
    return value


def main():
    args = cli_parse()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    url = get_url(args)
    js = load_json()

    html_doc = requests.get(url).text
    soup = bs4.BeautifulSoup(html_doc, 'html.parser')
    logger.info("Parsing URL {}".format(url))
    try:
        capis_meta = soup.find_all('a', class_="media-object")
        for capi_meta in capis_meta:
            p = re.compile('/video/([0-9]{7})/$')
            capis.append(p.search(capi_meta['href']).group(1))
    except:
        logger.error("Could not parse given url")
        sys.exit(2)

    capis.reverse()
    first_run = True
    new = False
    for capi in capis:
        logger.debug("Going for ID:{}".format(capi))
        try:
            html_doc = requests.get(subs1_urlbase + capi).text
            soup = bs4.BeautifulSoup(html_doc, 'html.parser')
            j = json.loads(soup.text)
            show = j['informacio']['programa']
        except:
            logger.error("Something went very wrong, can't parse second level url.")
            sys.exit(2)
        txt_file = list()

        if first_run:
            if show not in js:
                logger.debug("Show not in temporary file")
                js.append(show)
                js.append([])
                new = True
            pos = js.index(show) + 1
            first_run = False
        if not new:
            if capi in js[pos]:
                logger.debug("Episode already checked, skipping...")
                continue
        logger.debug("Going for multiple data.")
        # HEADER
        try:
            txt_file.append("{} {}".format(show, j['informacio']['capitol']))
        except KeyError:
            txt_file.append(show)
        # INFO
        txt_file.append("{}: {}".format(INFO_LINK, "{}{}".format(name_urlbase, capi)))

        # TITLE
        try:
            html_doc = requests.get(name_urlbase + capi).text
            soup = bs4.BeautifulSoup(html_doc, 'html.parser')
            txt_file.append("{}: {}".format(TITLE, soup.title.text))
        except:
            pass
        # MQ
        try:
            txt_file.append("{}: {}".format(MQ_VIDEO, soup.file.text))
        except:
            pass
        # HQ
        try:
            txt_file.append("{}: {}".format(HQ_VIDEO, j['media']['url']))
        except KeyError:
            pass
        # SUBS1
        try:
            txt_file.append("{}: {}".format(SUBTITLE_1, j['subtitols']['url']))
        except KeyError:
            pass
        # SUBS2
        try:
            html_doc = requests.get(subs2_urlbase + capi).text
            soup = bs4.BeautifulSoup(html_doc, 'html.parser')
            txt_file.append("{}: {}".format(SUBTITLE_2, soup.sub['url']))
        except:
            pass
        txt_file.append("")
        txt_file.append("")
        txt_file.append("")
        try:
            out_name_file = remove_invalid_win_chars(show, '\/:*?"<>|')
            outfile = open('%s.txt' % out_name_file, 'a')
            logger.info("Writing to {}".format(out_name_file))
            outfile.write('\n'.join(txt_file))
            outfile.close()
        except:
            logger.error("Writing episode to file failed.")
            sys.exit(1)
        js[pos].append(capi)
    create_json(js)


if __name__ == '__main__':
    main()
