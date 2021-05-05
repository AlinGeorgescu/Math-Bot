#!/usr/bin/env python3

"""
Alin Georgescu
University Politehnica of Bucharest
Faculty of Automatic Control and Computers
Computer Engeneering Department

Math Bot (C) 2021 - The agent's AI model

This code is part of "model/SiameseLSTM.ipynb". Some function and variable names
are changed with regard to the coding style conventions.
"""

import json
import random as rnd
import re

from collections import defaultdict

import numpy as np
import textcleaner as tc

from trax import layers as tl
from trax.fastmath import numpy as fastnp

def siamese(vocab_size, d_model=128):
    """Returns a Siamese model.

    Args:
        vocab_size (int, optional): Length of the vocabulary. Defaults to
                                    len(vocab).
        d_model (int, optional): Depth of the model. Defaults to 128.

    Returns:
        trax.layers.combinators.Parallel: A Siamese model.
    """

    def normalize(vec):  # normalizes the vectors to have L2 norm 1
        return vec / fastnp.sqrt(fastnp.sum(vec * vec, axis=-1, keepdims=True))

    s_processor = tl.Serial(
        tl.Embedding(vocab_size, d_model),  # Embedding layer
        tl.LSTM(d_model),                   # LSTM layer
        tl.Mean(axis=1),                    # Mean over columns
        tl.Fn('Normalize', normalize)       # Apply normalize function
    )  # Returns one vector of shape [batch_size, d_model].

    # Run on s1_tensor and s2_tensor in parallel.
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
    model = siamese(vocab_size=len(vocab))
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

def data_gen(sentences1, sentences2, batch_size, pad=1, shuffle=False):
    """Generator function that yields batches of data

    Args:
        sentences1 (list): List of transformed (to tensor) sentences.
        sentences2 (list): List of transformed (to tensor) sentences.
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
    len_s = len(sentences1)
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

        s1_tensor = sentences1[sentence_indexes[idx]]
        s2_tensor = sentences2[sentence_indexes[idx]]

        idx += 1

        input1.append(s1_tensor)
        input2.append(s2_tensor)

        if len(input1) == batch_size:
            # Determine max_len as the longest sentence in input1 & input 2
            max_len = max(max([len(s) for s in input1]),
                          max([len(s) for s in input2]))
            # Pad to power-of-2
            max_len = 2 ** int(np.ceil(np.log2(max_len)))

            tmp_out1 = []
            tmp_out2 = []
            for s1_tensor, s2_tensor in zip(input1, input2):
                # Add [pad] to s1_tensor until it reaches max_len
                s1_tensor = s1_tensor + [pad] * (max_len - len(s1_tensor))
                # Add [pad] to s2_tensor until it reaches max_len
                s2_tensor = s2_tensor + [pad] * (max_len - len(s2_tensor))

                # Append s1_tensor
                tmp_out1.append(s1_tensor)
                # Append s2_tensor
                tmp_out2.append(s2_tensor)

            # Use tmp_out1 and tmp_out2
            yield np.array(tmp_out1), np.array(tmp_out2)

            # reset the batches
            input1, input2 = [], []

def predict(sentences, threshold, model, vocab, data_generator=data_gen):
    """Function for predicting if two sentences are duplicates.

    Args:
        sentences ((str, str)): The tuple containing the sentences.
        threshold (float): Desired threshold.
        model (trax.layers.combinators.Parallel): The Siamese model.
        vocab (collections.defaultdict): The vocabulary used.
        data_gen (function): Data generator function. Defaults to data_gen.

    Returns:
        bool: True if the sentences are duplicates, False otherwise.
    """

    s1_tokens = data_tokenizer(sentences[0])  # tokenize
    s2_tokens = data_tokenizer(sentences[1])  # tokenize

    s1_tensor, s2_tensor = [], []

    for word in s1_tokens:  # encode sentence1
        s1_tensor += [vocab[word]]
    for word in s2_tokens:  # encode sentence2
        s2_tensor += [vocab[word]]

    s1_tensor, s2_tensor = \
            next(data_generator([s1_tensor], [s2_tensor], 1, vocab["<PAD>"]))

    vec1, vec2 = model((s1_tensor, s2_tensor))
    sim = np.dot(vec1[0], vec2[0].T)
    res = sim > threshold

    return res

if __name__ == "__main__":
    pass
