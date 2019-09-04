import requests
import lxml.html
import re
from nltk.corpus import stopwords
import pymorphy2
from collections import Counter

sw = stopwords.words('russian') + ['неё', 'её', 'всё']
print(sw)

site = 'http://astro-consul.ru/'
link_history = [site]
print('Сайт:', site)
response = requests.get(site)
if response.history:
    for i in response.history:
        print('Обранужен редирект с кодом', i.status_code)
    print('Конечный URL:', response.url)
if response.url not in link_history:
    link_history.append(response.url)
    site = response.url
print('Сбор ссылок на HTML-страницы...')
tree = lxml.html.fromstring(response.text)
links = tree.xpath('/html//a/@href')
links_set = list(set(links))
links_set = [x for x in links_set if x != '']
links_set = [x for x in links_set if '?' not in x]
for k in range(len(links_set)):
    if links_set[k] not in link_history:
        links_set[k] = site + links_set[k]
depth = 1
linkdepth = dict.fromkeys(links_set, depth)
newlinks = []
while (links_set):
    depth += 1
    for i in links_set:
        if (i not in link_history):
            response = requests.get(i)
            content_type = response.headers.get('Content-Type')
            if 'text/html' not in content_type:
                continue
            tree = lxml.html.fromstring(response.text)
            if response.url not in link_history:
                link_history.append(response.url)
                links2 = tree.xpath('/html//a/@href')
            links_set2 = list(set(links2))
            links_set2 = [x for x in links_set2 if x != '']
            links_set2 = [x for x in links_set2 if '?' not in x]
            for k in range(len(links_set2)):
                if links_set2[k] not in link_history:
                    links_set2[k] = site + links_set2[k]
            linksect = list(set(links_set).intersection(set(links_set2)))
            linkdif = list(set(links_set2) - set(linksect))
            linkdif = [x for x in linkdif if x not in link_history]
            if linkdif:
                newlinks = newlinks + linkdif
    newdepth = dict.fromkeys(newlinks, depth)
    linkdepth.update(newdepth)
    links_set = newlinks
    newlinks = []
html_links = []
for i in link_history:
    response = requests.get(i)
    content_type = response.headers.get('Content-Type')
    if ('text/html' in content_type) and (response.history == []):
        html_links.append(i)
print('Найдено', len(html_links), 'HTML-страниц:')
print(html_links)
print('Максимальный уровень вложенности страниц (количество кликов от главной страницы):', max(linkdepth.values()))
htmlmap = False
for i in html_links:
    response = requests.get(i)
    tree = lxml.html.fromstring(response.text)
    links = tree.xpath('/html//a/@href')
    links_set = list(set(links))
    links_set = [x for x in links_set if x != '']
    links_set = [x for x in links_set if '?' not in x]
    for k in range(len(links_set)):
        if links_set[k] not in link_history:
            links_set[k] = site + links_set[k]
    if links_set == html_links:
        print('Имеется HTML-карта сайта:', i)
        htmlmap = True
        break
if htmlmap == False:
    print('На сайте отсутствует HTML-карта сайта')
print('***********************************')
for i in html_links:
    response = requests.get(i)
    print(i)
    print('Код состояния:', response.status_code)
    print('Уровень вложенности:', linkdepth.get(i))
    struct_test = re.sub('\.html$', '', i)
    struct_test = re.sub(site, '', struct_test)
    struct_test = struct_test.split('/')
    struct_test = [x for x in struct_test if x != '']
    if len(struct_test) == linkdepth.get(i):
        print('Уровень вложенности отражен в URL.')
    else:
        print('Уровень вложенности некорректно отражен в URL. Подразумевается:', len(struct_test), '- Фактически:',
              linkdepth.get(i))
    tree = lxml.html.fromstring(response.text)
    text = tree.xpath('/html/body//text()')
    text = ''.join(text)
    text = text.lower()
    text = text.translate({ord(o): None for o in ('!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~–©•')})
    text = text.split()
    normal_text = [pymorphy2.MorphAnalyzer().parse(word)[0].normal_form for word in
                   text]
    normal_text = [x for x in normal_text if x not in sw]
    word_percent = Counter(normal_text)
    for key, value in word_percent.items():
        word_percent[key] = round(((value / len(text)) * 100), 2)
    print('10 самых употребляемых слов:', word_percent.most_common(10))
    top_words = []
    okay_percentage = []
    overused = []
    for key, value in word_percent.most_common(10):
        top_words.append(key)
        if 1.5 <= value <= 5:
            okay_percentage.append(key)
        if value > 5:
            overused.append(key)
    if okay_percentage:
        print('Из десяти наиболее употребляемых слов,', len(okay_percentage), 'имеют плотность от 1.5% до 5%:',
              okay_percentage, ' - потому они претендуют на звание ключевых')
    else:
        if not overused:
            print('На странице нет слов с плотностью выше 1.5%. Необходимо повысить плотность ключевых слов.')
    if overused:
        print('Следующие слова имеют плотность выше 5%:', overused,
              '- Если данные слова являются ключевыми, необходимо уменьшить их плотность.')
    titletags = tree.xpath('/html//title/text()')
    h1s = tree.xpath('/html//h1/text()')
    if len(titletags) > 1:
        print('Используется более одного тега <title>. Поисковыми системами и браузерами будет использоваться первый.')
    print('Title:', titletags[0])
    print('<h1>:', h1s)
    titletag = titletags[0]
    titletag = titletag.translate({ord(o): None for o in ('!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~–©•')})
    for h in range(len(h1s)):
        h1s[h] = h1s[h].translate({ord(o): None for o in ('!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~–©•')})
        h1s[h] = [pymorphy2.MorphAnalyzer().parse(word)[0].normal_form for word in h1s[h].lower().split()]
        h1s[h] = [x for x in h1s[h] if x not in sw]
    norm_title = [pymorphy2.MorphAnalyzer().parse(word)[0].normal_form for word in titletag.lower().split()]
    norm_title = [x for x in norm_title if x not in sw]
    norm_h1s = h1s
    if len(set(norm_title).intersection(top_words)) > 0:
        if 3 <= len(set(norm_title).intersection(top_words)) <= 5:
            print('Title содержит 3-5 часто употребляемых в тексте страницы слов.')
        if 1 <= len(set(norm_title).intersection(top_words)) <= 2:
            print(
                'Title содержит 1-2 часто употребляемых в тексте страницы слова. Рекомендуется увеличить это количество на 2-3 слова.')
        if len(set(norm_title).intersection(top_words)) > 5:
            print('Title содержит более 5 ключевых слов. Рекомендуется уменьшить это количество.')
    else:
        print('Заголовок не содержит часто употребляемых в тексте страницы слов.')
    for j in range(len(norm_h1s)):
        if len(set(norm_title).intersection(norm_h1s[j])) == 0:
            print('Title и '+str(j+1)+'-й H1 не пересекаются. Следует обеспечить пересечение по важным ключевым словам.')
        if norm_title == norm_h1s[j]:
            print('Title и '+str(j+1)+'-й H1 совпадают. Следует сделать их различными, обеспечив пересечение по важным ключевым словам.')
    schemas = tree.xpath('/html//@itemtype')
    schema_usage = False
    if schemas:
        for k in range(len(schemas)):
            schemas[k].lower()
            if 'http://schema.org/' in schemas[k]:
                schema_usage = True
                schema_type = re.sub('http://schema.org/', '', schemas[k])
                print('На данной странице есть использование Schema.org. Вид данных:', schema_type)
    if schema_usage == False:
        print('Атрибуты Schema.org не используются на данной странице')
    metatags = tree.xpath('/html/head/meta')
    ctype_exists = False
    desc_exists = False
    keyw_exists = False
    vport_exists = False
    for m in range(len(metatags)):
        metahttp = tree.xpath('/html/head/meta[' + str(m + 1) + ']/@http-equiv')
        if 'content-type' in metahttp:
            ctype_exists = True
            metactype = tree.xpath('/html/head/meta[' + str(m + 1) + ']/@content')
            metactype = ''.join(metactype)
            if 'charset' in metactype:
                print('Мета Content-Type: content="' + metactype + '"')
            if metactype == '':
                print('Мета-тег Content-Type не заполнен.')
    for m in range(len(metatags)):
        metaname = tree.xpath('/html/head/meta[' + str(m + 1) + ']/@name')
        if 'viewport' in metaname:
            vport_exists = True
            metaview = tree.xpath('/html/head/meta[' + str(m + 1) + ']/@content')
            metaview = ''.join(metaview)
            if metaview == '':
                print(
                    'Мета-тег viewport не заполнен. Необходимо заполнить его по типу content="width=device-width" с целью улучшения страницы отображения на мобильных устройствах.')
            if 'width=' in metaview:
                print('Meta Viewport: content="' + metaview + '"')
        if 'description' in metaname:
            desc_exists = True
            metadesc = tree.xpath('/html/head/meta[' + str(m + 1) + ']/@content')
            metadesc = ''.join(metadesc)
            if metadesc == '':
                print('Незаполненный мета-тег description')
            else:
                print('Meta Description:', metadesc)
        if 'keywords' in metaname:
            keyw_exists = True
            metakeys = tree.xpath('/html/head/meta[' + str(m + 1) + ']/@content')
            metakeys = ''.join(metakeys)
            if metakeys == '':
                print('Незаполненный мета-тег keywords')
            else:
                print('Meta Keywords:', metakeys)
                if len(metakeys.replace(',', '').split()) > 6:
                    print(
                        'Рекомендуется уменьшить количество слов в мета-теге keywords во избежание потенциальных санкций')
    if desc_exists == False:
        print(
            'Мета-тег description отсутствует. Рекомендуется добавить описание страницы для отображения его на страницах поисковой выдачи.')
    if keyw_exists == False:
        print(
            'Мета-тег keywords отсутствует. Рекомендуется добавить ввиду использования его некоторыми поисковыми системами.')
    if vport_exists == False:
        print(
            'Мета-тег viewport отсутствует. Рекомендуется добавить для корректного отображения страницы на мобильных устройствах.')
    if ctype_exists == False:
        print(
            'Мета-тег Content-Type, необходимый для определения кодировки, отсутствует. Рекомендуется добавить во избежание проблем с отображением страницы.')
    alts = tree.xpath('/html//@alt')
    empty_alts = False
    if alts:
        print('Содержимое атрибутов alt:', alts)
        for l in range(len(alts)):
            if alts[l] == '':
                empty_alts = True
        if empty_alts == True:
            print('Обнаружены незаполненные атрибуты alt. Рекомендуется их заполнить.')
    print('***********************************\n')