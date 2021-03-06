# -*- coding:utf-8 -*-
import numpy as np 
import pandas as pd 
import jieba
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
import pickle, os
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB  
from sklearn.metrics.pairwise import cosine_similarity


#加停用词
with open(r'chinese_stopwords.txt', 'r', encoding='utf-8') as file:
	stopwords = [i[:-1] for i in file.readlines()]

#数据加载
news = pd.read_csv('sqlResult.csv', encoding='gb18030')
print(news.shape)

#处理缺失值
print(news[news.content.isna()].head())
news = news.dropna(subset=['content'])
print(news.shape)

#分词
def split_text(text):
	text = text.replace(' ','')
	text = text.replace('\n','')
	text2 = jieba.cut(text.strip())
	result = ' '.join([w for w in text2 if w not in stopwords])
	return result

print(news.iloc[0].content)
print(split_text(news.iloc[0].content))


if not os.path.exists('corpus.pkl'):
	corpus = list(map(split_text, [str(i) for i in news.content]))
	print(corpus[0])
	print(len(corpus))
	print(corpus[1])
	with open(r'corpus.pkl', 'wb') as file:
		pickle.dump(corpus, file)
else:
	with open(r'corpus.pkl', 'rb') as file:
		corpus = pickle.load(file)

#计算corpus的TF-IDF矩阵
countvectorizer = CountVectorizer(encoding='gb18030', min_df = 0.015)
tfidftransformer = TfidfTransformer()
countvector = countvectorizer.fit_transform(corpus)
tfidf = tfidftransformer.fit_transform(countvector)
print(tfidf.shape)

#标记是否是自己的新闻
label = list(map(lambda source: 1 if '新华' in str(source) else 0, news.source))

#数据切分
X_train, X_test, y_train, y_test = train_test_split(tfidf.toarray(), label, test_size=0.3, random_state=33)
clf = MultinomialNB()
#分类器使用的是fit和predict
clf.fit(X_train, y_train)
prediction = clf.predict(tfidf.toarray())
labels = np.array(label)

compare_new_index = pd.DataFrame({'prediction': prediction, 'labels': labels})
#计算所有可疑文章的index
copy_news_index = compare_new_index[(compare_new_index['prediction']==1) & (compare_new_index['labels']==0)].index
#计算所有新华社文章的index
xinhuashe_news_index = compare_new_index[(compare_new_index['labels'] == 1)].index
print('可疑文章数：',len(copy_news_index))


from sklearn.cluster import KMeans
from sklearn import preprocessing
from sklearn.preprocessing import Normalizer
normalizer = Normalizer()
scaled_array = normalizer.fit_transform(tfidf.toarray())

if not os.path.exists('label.pkl'):
	#使用kmeans，对全量文档做聚类
	kmeans = KMeans(n_clusters=25)
	k_labels = kmeans.fit_predict(scaled_array)
	with open('label.pkl', 'wb') as file:
		pickle.dump(k_labels, file)
	print('k_labels.shape', k_labels.shape)
else:
	with open('label.pkl', 'rb') as file:
		k_labels = pickle.load(file)

if not os.path.exists('id_class.pkl'):
	#创建id_class
	id_class = {index:class_ for index, class_ in enumerate(k_labels)}
	with open('id_class.pkl', 'wb') as file:
		pickle.dump(k_labels, file)
else:
	with open('id_class.pkl', 'rb') as file:
		id_class = pickle.load(file)

if not os.path.exists('class_id.pkl'):
	from collections import defaultdict
	#创建class_id
	class_id = defaultdict(set)
	for index, class_ in id_class.items():
		#只统计新华社发布的class_id
		if index in xinhuashe_news_index.tolist():
			class_id[class_].add(index)
	with open('class_id.pkl', 'wb') as file:
		pickle.dump(class_id, file)
else:
	with open('class_id.pkl', 'rb') as file:
		class_id = pickle.load(file)

#想找相似文本
def find_similar_text(cpindex, top=10):
	#只在新华社发布的文章中进行查找
	dist_dict = {i:cosine_similarity(tfidf[cpindex], tfidf[i]) for i in class_id[id_class[cpindex]]}
	#从小到大进行排序
	return sorted(dist_dict.items(), key=lambda x:x[1][0], reverse=True)[:top]

cpindex = 3352
similar_list = find_similar_text(cpindex)
print(similar_list)
print('怀疑抄袭:\n', news.iloc[cpindex].content)
#找一篇相似的原文
similar2 = similar_list[0][0]
print('相似原文\n', news.iloc[similar2].content)

import editdistance
#看下两篇文章之间的编辑距离
print('编辑距离：', editdistance.eval(corpus[cpindex], corpus[similar2]))
