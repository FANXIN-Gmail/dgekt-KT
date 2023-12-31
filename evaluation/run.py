import sys
import os
sys.path.append('../..')

CUDA_VISIBLE_DEVICES = 0
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from KnowledgeTracing.DirectedGCN.load_data import get_adj
from KnowledgeTracing.BipartiteGCN import BPR
from KnowledgeTracing.hgnn_models import hypergraph_utils as hgut
from KnowledgeTracing.model.Model import DKT
from KnowledgeTracing.data.dataloader import getLoader
from KnowledgeTracing.Constant import Constants as C
from torch import optim as optima
from KnowledgeTracing.evaluation import eval
import torch
import logging
from datetime import datetime
import numpy as np
import warnings
import random
import pandas as pd

warnings.filterwarnings('ignore')

torch.cuda.set_device(0)

path_save_model_base='../model/' + C.RUN_ID
if (os.path.exists(path_save_model_base)):
    print('has model save path')
else:
    os.makedirs(path_save_model_base)

'''check cuda'''
use_gpu = torch.cuda.is_available()
device = torch.device('cuda')
print('GPU state: ', use_gpu)
print('GPU name: ', torch.cuda.get_device_name(CUDA_VISIBLE_DEVICES))
print('Dataset: ' + C.DATASET + ', Ques number: ' + str(C.NUM_OF_QUESTIONS) + '\n')

''' save log '''
logger = logging.getLogger('main')
logger.setLevel(level=logging.DEBUG)
date = datetime.now()
handler = logging.FileHandler(
    f'log/{date.year}_{date.month}_{date.day}_result.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info('This is a new training log')
logger.info('\nDataset: ' + str(C.DATASET) + ', Ques number: ' + str(C.NUM_OF_QUESTIONS) + ', Batch_size: ' + str(
    C.BATCH_SIZE))

'''set random seed'''

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    os.environ['CUDA_VISIBLE_DEVICES'] = '0,2'
    os.environ['PYTHONHASHSEED'] = str(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

set_seed(216)

trainLoaders, testLoaders = getLoader(C.DATASET)

loss_func = eval.lossFunc(C.HIDDEN, C.MAX_STEP, device)

def KTtrain():
    adj = hgut.generate_G_from_H(pd.read_csv(r'../../Dataset/H/' + C.H + '.csv', header=None))
    bipartite_G = BPR.bipartite(trainLoaders, testLoaders)
    G = adj.cuda()
    adj_out, adj_in = get_adj()
    adj_in = adj_in.cuda()
    adj_out = adj_out.cuda()
    model = DKT(C.HIDDEN, C.LAYERS, G, adj_out, adj_in, bipartite_G).cuda()
    optimizer = optima.Adam(model.parameters(), lr=C.LR)

    best_auc = 0.0
    best_epoch = 0
    best_acc = 0.0
    for epoch in range(C.EPOCH):
        print('epoch: ' + str(epoch + 1) + '            lr = ', optimizer.param_groups[0]["lr"])
        model, optimizer = eval.train_epoch(model, trainLoaders[0], optimizer, loss_func)
        logger.info(f'epoch {epoch + 1}')
        with torch.no_grad():
            auc, acc, loss = eval.test_epoch(model, testLoaders[0], loss_func, device)
            if best_auc < auc:
                best_auc = auc
                best_acc = acc
                best_epoch = epoch + 1
                torch.save(model, path_save_model_base + "/epoch" + str(epoch) + '.pkl')

            print('Best auc at present: %f  acc:  %f  Best epoch: %d' % (best_auc, best_acc, best_epoch))

def KTtest():
    model = torch.load(path_save_model_base + "/epoch" + str(epoch) + '.pkl')
    print('loading the best model...')
    with torch.no_grad():
        eval.test_epoch(model, testLoaders[0], loss_func, device)

KTtrain()
# KTtest()