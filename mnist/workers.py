from __future__ import print_function

import argparse
import tensorflow as tf
from timer import Timer
import mnist
import pbt
import test_accuracy
import train_graph as train_
import overfit_score
import hparams as hp


def main(args):
    main_time = Timer()
    dataset = mnist.get_dataset(args.dataset)
    mnist.gen_model(args.model, args.loss)

    print('step, worker, samples, time, loops, learnrate, batchsize, trainaccuracy, testaccuracy, validation')

    workers = build_workers(args.popsize, dataset,
                            [hp.resample_learnrate, hp.resample_batchsize],
                            [hp.perturb_learnrate, hp.perturb_batchsize])

    train_workers(workers, args.train_time, args.steps, args.popshrink, pbt.pbt)

    print('# total time %3.1f' % main_time.elapsed())


def build_workers(popsize, dataset, hparams_fun=None, perturb_fun=None):
    build_time = Timer()
    init_op = tf.get_collection('init_op')[0]

    saver = tf.train.Saver(max_to_keep=popsize)

    with tf.Session() as sess:
        workers = []
        for i in range(popsize):
            sess.run(init_op)
            name = 'ckpt/worker_' + str(i) + '.ckpt'
            saver.save(sess, name)
            hparams = [fun() for fun in hparams_fun]
            worker = {'name': name, 'dup_from_name': None, 'id': i, 'score': 0.0,
                      'hparams': hparams, 'resample': hparams_fun, 'perturb': perturb_fun,
                      'dataset': dataset}
            workers.append(worker)

            # print('# worker (%d) setup time %3.1f' % (i, build_time.split()))
        print('# total setup time %3.1f' % build_time.elapsed())
    sess.close()
    return workers


def train_workers(workers, train_time, training_steps, popshrink=1.0, step_callback=None, test_size=1000):
    step_time = Timer()
    for step in range(1, training_steps + 1):
        io_accum = 0.0
        for worker in workers:
            print('%d, ' % step, end='')
            io_accum += train_worker(worker, train_time, test_size)
        if step_callback:
            step_callback(workers, popshrink=popshrink)
        print('# step time %3.1fs, ' % step_time.split(), end='')
        print('# io time %3.1fs' % io_accum)


def train_worker(worker, train_time, test_size):
    io_time = Timer()
    io_accum = 0.0
    tf.reset_default_graph()
    with tf.Session() as sess:
        io_time.split()
        name = worker['dup_from_name'] or worker['name']
        saver2 = tf.train.import_meta_graph(name + '.meta')
        saver2.restore(sess, name)
        worker['dup_from_name'] = None
        io_accum += io_time.split()
        print('%d, ' % worker['id'], end='')
        trainscore, testscore = train_graph(
            sess, train_time, worker['hparams'][1], test_size, worker['hparams'][0], worker['dataset'])
        worker['score'] = overfit_score.overfit_blended(trainscore, testscore)
        io_time.split()
        saver2.save(sess, worker['name'])
        io_accum += io_time.split()
    return io_accum


def train_graph(sess, train_time, batch_size, test_size, learn_rate, dataset, train_step=None):
    if train_step is None:
        train_step = tf.get_collection('train_step')[0]
    x = tf.get_collection('x')[0]
    y_ = tf.get_collection('y_')[0]
    learning_rate = tf.get_collection('learning_rate')[0]
    accuracy = tf.get_collection('accuracy')[0]

    batch_time = Timer()
    iterations = 50
    total_iterations = 0
    count = 0
    while batch_time.elapsed() < train_time:
        train_.iterate_training(sess, iterations, batch_size, learn_rate, dataset, x, y_, train_step, learning_rate)
        count += 1
        total_iterations += iterations

    print('%d, %f, %d, ' % (total_iterations * batch_size, batch_time.split(), count), end='')
    print('%g, ' % learn_rate, end='')
    print('%d, ' % batch_size, end='')

    testdata_size = len(dataset.test.labels)
    trainscore = test_accuracy.test_accuracy(sess, dataset.train, testdata_size, test_size, x, y_, accuracy, True)
    testscore = test_accuracy.test_accuracy(sess, dataset.test, testdata_size, test_size, x, y_, accuracy)
    validscore = test_accuracy.test_accuracy(sess, dataset.validation, testdata_size, test_size, x, y_, accuracy)

    print('%f, ' % trainscore, end='')
    print('%f, ' % testscore, end='')
    print('%f' % validscore)

    return (trainscore, testscore)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', nargs='?', default="bias_layer", help="tensorflow model")
    parser.add_argument('--loss', nargs='?', default="softmax", help="tensorflow loss")
    parser.add_argument('--popsize', nargs='?', type=int, default=10, help="number of workers (10)")
    parser.add_argument('--popshrink', nargs='?', type=float, default=1.0,
                        help="fraction of population to keep after each step (1.0)")
    parser.add_argument('--train_time', nargs='?', type=float, default=10.0,
                        help="training time per worker per step (10.0s)")
    parser.add_argument('--steps', nargs='?', type=int, default=10, help="number of training steps (10)")
    parser.add_argument('--dataset', type=str, choices=['mnist', 'fashion'], default='mnist', help='name of dataset')
    main(parser.parse_args())
