"""
Tests for attention module
"""
import numpy as np
import theano
import theano.tensor as T
import agentnet
from agentnet.memory import GRUCell
from agentnet.memory.attention import AttentionLayer
from lasagne.layers import *


def test_attention():
    """
    minimalstic test that showcases attentive RNN that reads some chunk
    of input sequence on each tick and outputs nothing
    """

    # step inner graph
    class step:
        enc_activations = InputLayer((None, None, 12), name='placeholder for encoder activations (to be attended)')
        prev_gru = InputLayer((None, 15),name='gru prev state (15 units)')

        attention = AttentionLayer(enc_activations,prev_gru,num_units=16)

        gru = GRUCell(prev_gru, attention['attn'] , name='rnn that reads enc_sequence with attention')

        attn_probs = attention['probs'] #weights from inside attention

    # outer graph


    encoder_activations = InputLayer((None,None,12),name='encoder sequence (will be sent to enc_sequence)')

    rec = agentnet.Recurrence(input_nonsequences={step.enc_activations: encoder_activations},
                              state_variables={step.gru: step.prev_gru},
                              tracked_outputs=[step.attn_probs],

                              unroll_scan=False,
                              n_steps = 10)

    weights = get_all_params(rec)

    gru_states,attention_probs_seq = rec[step.gru,step.attn_probs]

    run = theano.function([encoder_activations.input_var], get_output([gru_states,attention_probs_seq]),
                          updates=rec.get_automatic_updates(),allow_input_downcast=True)

    #run on surrogate data
    gru_seq,probs_seq = run(np.random.randn(5, 25, 12))

    assert gru_seq.shape == (5, 10, 15) #hidden GRU strates, 5 samples/10ticks/15units
    assert probs_seq.shape == (5, 10, 25) #attention sequences, 5 samples/10ticks/25 input seq length

    #hard attention
    hard_outputs = get_output([gru_states,attention_probs_seq],recurrence_flags={'hard_attention':True})

    hard_run = theano.function([encoder_activations.input_var], hard_outputs,
                                updates=rec.get_automatic_updates(),allow_input_downcast=True)

    #run on surrogate data
    _,hard_probs_seq = hard_run(np.random.randn(5, 25, 12))

    #check if probs are one-hot
    assert hard_probs_seq.shape == (5, 10, 25) #attention sequences, 5 samples/10ticks/25 input seq length
    assert len(np.unique(hard_probs_seq.ravel()))==2  #only 0's and 1's


def test_attention_2d():
    """
    Almost a copy-paste of previous test, but this time attention is applied to an image instead
    of a 1d sequence.
    """

    # step inner graph
    class step:
        image = InputLayer((None,3,24,24), name='placeholder for 24x24 image (to be attended)')
        prev_gru = InputLayer((None, 15),name='gru prev state (15 units)')

        #get image dimensions
        n_channels,width,height = image.output_shape[1:]

        #flatten all image spots to look like 1d sequence
        image_chunks = reshape(dimshuffle(image,[0,2,3,1]),(-1,width*height,n_channels))

        attention = AttentionLayer(image_chunks,prev_gru,num_units=16)

        gru = GRUCell(prev_gru, attention['attn'] , name='rnn that reads enc_sequence with attention')

        #weights from inside attention - reshape back into image
        attn_probs = reshape(attention['probs'],(-1,width,height))


    # outer graph


    input_image = InputLayer((None,3,24,24),name='24x24-pixel RGB image to be sent into step.image')

    rec = agentnet.Recurrence(input_nonsequences={step.image: input_image},
                              state_variables={step.gru: step.prev_gru},
                              tracked_outputs=[step.attn_probs],
                              unroll_scan=False,
                              n_steps = 10)

    weights = get_all_params(rec)

    gru_states,attention_probs_seq = rec[step.gru,step.attn_probs]

    run = theano.function([input_image.input_var], get_output([gru_states,attention_probs_seq]),
                          updates=rec.get_automatic_updates(),allow_input_downcast=True)

    #run on surrogate data
    gru_seq,probs_seq = run(np.random.randn(5, 3, 24,24))

    assert gru_seq.shape == (5, 10, 15) #hidden GRU strates, 5 samples/10ticks/15units
    assert probs_seq.shape == (5, 10, 24,24) #attention sequences, 5 samples/10ticks/24width/24height

from agentnet.memory.attention import DotAttentionLayer

def test_dot_attention():
    """
    minimalstic test that showcases attentive RNN that reads some chunk
    of input sequence on each tick and outputs nothing.
    
    This time it uses DotAttention [aka multiplicative attention] instead of regular one.
    """

    # step inner graph
    class step:
        enc_activations = InputLayer((None, None, 12), name='placeholder for encoder activations (to be attended)')
        prev_gru = InputLayer((None, 15),name='gru prev state (15 units)')

        attention = DotAttentionLayer(enc_activations,prev_gru,use_dense_layer=True)

        gru = GRUCell(prev_gru, attention['attn'] , name='rnn that reads enc_sequence with attention')

        attn_probs = attention['probs'] #weights from inside attention

    # outer graph


    encoder_activations = InputLayer((None,None,12),name='encoder sequence (will be sent to enc_sequence)')

    rec = agentnet.Recurrence(input_nonsequences={step.enc_activations: encoder_activations},
                              state_variables={step.gru: step.prev_gru},
                              tracked_outputs=[step.attn_probs],

                              unroll_scan=False,
                              n_steps = 10)

    weights = get_all_params(rec)

    gru_states,attention_probs_seq = rec[step.gru,step.attn_probs]

    run = theano.function([encoder_activations.input_var], get_output([gru_states,attention_probs_seq]),
                          updates=rec.get_automatic_updates(),allow_input_downcast=True)

    #run on surrogate data
    gru_seq,probs_seq = run(np.random.randn(5, 25, 12))

    assert gru_seq.shape == (5, 10, 15) #hidden GRU strates, 5 samples/10ticks/15units
    assert probs_seq.shape == (5, 10, 25) #attention sequences, 5 samples/10ticks/25 input seq length

    #hard attention
    hard_outputs = get_output([gru_states,attention_probs_seq],recurrence_flags={'hard_attention':True})

    hard_run = theano.function([encoder_activations.input_var], hard_outputs,
                                updates=rec.get_automatic_updates(),allow_input_downcast=True)

    #run on surrogate data
    _,hard_probs_seq = hard_run(np.random.randn(5, 25, 12))

    #check if probs are one-hot
    assert hard_probs_seq.shape == (5, 10, 25) #attention sequences, 5 samples/10ticks/25 input seq length
    assert len(np.unique(hard_probs_seq.ravel()))==2  #only 0's and 1's



from agentnet.memory.attention import self_attention, multihead_attention

def test_self_attention():
    """This tests parallel computation of self-attention, 
    where each element of next hidden sequence casts attention into previous hidden sequence.

    This is vaguely inspired by https://arxiv.org/abs/1706.03762.
    """
    VOCAB_SIZE = 100
    BATCH_SIZE = 10
    SEQ_LENGTH = 20
    input_var = T.arange(BATCH_SIZE * SEQ_LENGTH).reshape([BATCH_SIZE, SEQ_LENGTH]) % VOCAB_SIZE

    l_inp = InputLayer((None, None), input_var)
    l_emb = EmbeddingLayer(l_inp, VOCAB_SIZE, 32)
    l_self_attn = self_attention(l_emb, key_size=48,value_size=50)
    l_self_attn2 = self_attention(l_self_attn, key_size=64,value_size=100)

    out = get_output(l_self_attn2).eval()

    assert tuple(out.shape)==(BATCH_SIZE,SEQ_LENGTH,100)


def test_multihead_attention():
    """
    minimalstic test that showcases attentive RNN that reads some chunk
    of input sequence on each tick and outputs nothing.

    This time it uses Multihead DotAttention [aka multiplicative attention] instead of regular one.
    """

    # step inner graph
    class step:
        enc_activations = InputLayer((None, None, 12), name='placeholder for encoder activations (to be attended)')
        prev_gru = InputLayer((None, 15), name='gru prev state (15 units)')

        keys_seq = DenseLayer(enc_activations,30,num_leading_axes=2,nonlinearity=None)

        attention = multihead_attention(enc_activations, prev_gru,
                                        key_sequence = keys_seq,
                                        num_heads=3, use_dense_layer=True,)

        gru = GRUCell(prev_gru, attention['attn'], name='rnn that reads enc_sequence with attention')

        attn, attn_probs = attention['attn'],attention['probs']  # weights from inside attention

    # outer graph


    encoder_activations = InputLayer((None, None, 12), name='encoder sequence (will be sent to enc_sequence)')

    rec = agentnet.Recurrence(input_nonsequences={step.enc_activations: encoder_activations},
                              state_variables={step.gru: step.prev_gru},
                              tracked_outputs=[step.attn_probs,step.attn],

                              unroll_scan=False,
                              n_steps=10)

    weights = get_all_params(rec)

    gru_states, attn_heads_seq, attention_probs_seq = rec[step.gru, step.attn, step.attn_probs]

    run = theano.function([encoder_activations.input_var], get_output([gru_states, attn_heads_seq, attention_probs_seq]),
                          updates=rec.get_automatic_updates(), allow_input_downcast=True)

    # run on surrogate data
    gru_seq, heads_seq, probs_seq = run(np.random.randn(5, 25, 12))

    assert gru_seq.shape == (5, 10, 15)  # hidden GRU strates, 5 samples/10ticks/15units
    assert probs_seq.shape == (5, 10, 3, 25)  # attention sequences, 5 samples/10ticks/3heads/25 input seq length
    assert heads_seq.shape == (5, 10, 3*12)  # attention sequences, 5 samples/10ticks/3heads*30units
    # hard attention
    hard_outputs = get_output([gru_states, attention_probs_seq], recurrence_flags={'hard_attention': True})

    hard_run = theano.function([encoder_activations.input_var], hard_outputs,
                               updates=rec.get_automatic_updates(), allow_input_downcast=True)

    # run on surrogate data
    _, hard_probs_seq = hard_run(np.random.randn(5, 25, 12))

    # check if probs are one-hot
    assert hard_probs_seq.shape == (5, 10, 3, 25)  # attention sequences, 5 samples/10ticks/3heads/25 input seq length
    assert len(np.unique(hard_probs_seq.ravel())) == 2  # only 0's and 1's
