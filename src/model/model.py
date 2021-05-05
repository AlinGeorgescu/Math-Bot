#!/usr/bin/env python3

"""
Alin Georgescu
University Politehnica of Bucharest
Faculty of Automatic Control and Computers
Computer Engeneering Department

Math Bot (C) 2021 - The agent's AI model

This code is part of "model/SiameseLSTM.ipynb"
"""

import json
import re

import numpy as np
import random as rnd
import textcleaner as tc

from trax import layers as tl
from trax.fastmath import numpy as fastnp

from collections import defaultdict

def Siamese(vocab_size, d_model=128, mode="train"):
    """Returns a Siamese model.

    Args:
        vocab_size (int, optional): Length of the vocabulary. Defaults to
                                    len(vocab).
        d_model (int, optional): Depth of the model. Defaults to 128.
        mode (str, optional): "train", "eval" or "predict", predict mode is for
                              fast inference. Defaults to "train".

    Returns:
        trax.layers.combinators.Parallel: A Siamese model.
    """

    def normalize(x):  # normalizes the vectors to have L2 norm 1
        return x / fastnp.sqrt(fastnp.sum(x * x, axis=-1, keepdims=True))

    s_processor = tl.Serial(                        # Will run on S1 and S2
        tl.Embedding(vocab_size, d_model),          # Embedding layer
        tl.LSTM(d_model, mode=mode),                # LSTM layer
        tl.Mean(axis=1),                            # Mean over columns
        tl.Fn('Normalize', lambda x: normalize(x))  # Apply normalize function
    )  # Returns one vector of shape [batch_size, d_model].

    # Run on S1 and S2 in parallel.
    model = tl.Parallel(s_processor, s_processor)
    return model

def data_loader():
    """Loads the vocabulary and the model from files.

    Returns:
        (defaultdict, trax.layers.combinators.Parallel): A tuple containing the
                                               vocabulary and the Siamese model.
    """

    with open("data/en_vocab.txt", "r") as fin:
        vocab_dict = json.load(fin)

    vocab = defaultdict(lambda: 0, vocab_dict)
    model = Siamese(vocab_size=len(vocab))
    model.init_from_file("trax_model/model.pkl.gz")

    return (vocab, model)

def data_tokenizer(sentence):
    """Tokenizer function - cleans and tokenizes the data

    Args:
        sentence (str): The input sentence.
    Returns:
        list: The transformed input sentence.
    """

    if sentence == "":
        return ""

    sentence = tc.lower_all(sentence)[0]

    # Change tabs to spaces
    sentence = re.sub(r"\t+_+", " ", sentence)
    # Change short forms
    sentence = re.sub(r"\'ve", " have", sentence)
    sentence = re.sub(r"(can\'t|can not)", "cannot", sentence)
    sentence = re.sub(r"n\'t", " not", sentence)
    sentence = re.sub(r"I\'m", "I am", sentence)
    sentence = re.sub(r" m ", " am ", sentence)
    sentence = re.sub(r"(\'re| r )", " are ", sentence)
    sentence = re.sub(r"\'d", " would ", sentence)
    sentence = re.sub(r"\'ll", " will ", sentence)
    sentence = re.sub(r"(\d+)(k)", r"\g<1>000", sentence)
    # Make word separations
    sentence = re.sub(r"(\+|-|\*|\/|\^|\.)", " $1 ", sentence)
    # Remove irrelevant stuff, nonprintable characters and spaces
    sentence = re.sub(r"(\'s|\'S|\'|\"|,|[^ -~]+)", "", sentence)
    sentence = tc.strip_all(sentence)[0]
    # Remove dot (encoded by textcleaner with $1), if necessary
    sentence = re.sub(r" *\$1 *$", "", sentence)

    if sentence == "":
        return ""

    return tc.token_it(tc.lemming(tc.stemming(sentence)))[0]

def data_generator(S1, S2, batch_size, pad=1, shuffle=False, verbose=False):
    """Generator function that yields batches of data

    Args:
        S1 (list): List of transformed (to tensor) sentences.
        S2 (list): List of transformed (to tensor) sentences.
        batch_size (int): Number of elements per batch.
        pad (int, optional): Pad character from the vocab. Defaults to 1.
        shuffle (bool, optional): If the batches should be randomnized or not.
                                  Defaults to False.
        verbose (bool, optional): If the results should be printed out.
                                  Defaults to False.
    Yields:
        tuple: Of the form (input1, input2) with types
               (numpy.ndarray, numpy.ndarray)
        NOTE: input1: inputs to your model [s1a, s2a, s3a, ...] i.e. (s1a,s1b)
                      are duplicates
              input2: targets to your model [s1b, s2b,s3b, ...] i.e. (s1a,s2i)
                      i!=a are not duplicates
    """

    input1 = []
    input2 = []
    idx = 0
    len_s = len(S1)
    sentence_indexes = [*range(len_s)]

    if shuffle:
        rnd.shuffle(sentence_indexes)

    while True:
        if idx >= len_s:
            # If idx is greater than or equal to len_q, reset it
            idx = 0
            # Shuffle to get random batches if shuffle is set to True
            if shuffle:
                rnd.shuffle(sentence_indexes)

        s1 = S1[sentence_indexes[idx]]
        s2 = S2[sentence_indexes[idx]]

        idx += 1

        input1.append(s1)
        input2.append(s2)

        if len(input1) == batch_size:
            # Determine max_len as the longest sentence in input1 & input 2
            max_len = max(max([len(s) for s in input1]),
                          max([len(s) for s in input2]))
            # Pad to power-of-2
            max_len = 2 ** int(np.ceil(np.log2(max_len)))

            b1 = []
            b2 = []
            for s1, s2 in zip(input1, input2):
                # Add [pad] to s1 until it reaches max_len
                s1 = s1 + [pad] * (max_len - len(s1))
                # Add [pad] to s2 until it reaches max_len
                s2 = s2 + [pad] * (max_len - len(s2))

                # Append s1
                b1.append(s1)
                # Append s2
                b2.append(s2)

            if verbose == True:
                print("input1 = ", input1, "\ninput2 = ", input2)
                print("b1     = ", b1, "\nb2     = ", b2)

            # Use b1 and b2
            yield np.array(b1), np.array(b2)

            # reset the batches
            input1, input2 = [], []

def predict(sentence1, sentence2, threshold, model, vocab,
            data_generator=data_generator, verbose=False):
    """Function for predicting if two sentences are duplicates.

    Args:
        sentence1 (str): First sentence.
        sentence2 (str): Second sentence.
        threshold (float): Desired threshold.
        model (trax.layers.combinators.Parallel): The Siamese model.
        vocab (collections.defaultdict): The vocabulary used.
        data_generator (function): Data generator function. Defaults to
                                   data_generator.
        verbose (bool, optional): If the results should be printed out.
                                  Defaults to False.

    Returns:
        bool: True if the sentences are duplicates, False otherwise.
    """

    s1 = data_tokenizer(sentence1)  # tokenize
    s2 = data_tokenizer(sentence2)  # tokenize
    S1, S2 = [], []

    for word in s1:  # encode s1
        S1 += [vocab[word]]
    for word in s2:  # encode s2
        S2 += [vocab[word]]

    S1, S2 = next(data_generator([S1], [S2], 1, vocab["<PAD>"], False, verbose))

    v1, v2 = model((S1, S2))
    d = np.dot(v1[0], v2[0].T)
    res = d > threshold

    if verbose == True:
        print("S1  = ", S1, "\nS2  = ", S2)
        print("d   = ", d)
        print("res = ", res)

    return res

if __name__ == "__main__":
    pass
