from __future__ import print_function

import sys
import argparse
from importlib import import_module

import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data


def main(args):
    mnist = input_data.read_data_sets('input_data/', one_hot=True)
    x = tf.placeholder(tf.float32, [None, 784])
    y_ = tf.placeholder(tf.float32, [None, 10])

    model = import_module(args.model)
    loss = import_module(args.loss)

    y = model.make_model(x, y_)
    loss_fn = loss.make_loss(y, y_)
    train_step = tf.train.GradientDescentOptimizer(args.learning_rate).minimize(loss_fn)

    with tf.Session() as sess:
        tf.global_variables_initializer().run()

        train_model(args.iterations, x, y_, train_step, mnist, sess)
        test_model(x, y, y_, mnist, sess)


def train_model(iterations, x, y_, train_step, mnist, sess):
    for _ in range(iterations):
        batch_xs, batch_ys = mnist.train.next_batch(100)
        sess.run(train_step, feed_dict={x: batch_xs, y_: batch_ys})


def test_model(x, y, y_, mnist, sess):
    correct_prediction = tf.equal(tf.argmax(y, 1), tf.argmax(y_, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
    print(sess.run(accuracy, feed_dict={x: mnist.test.images,
                                        y_: mnist.test.labels}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', nargs='?',
                        default="bias_layer", help="tensorflow model")
    parser.add_argument('--loss', nargs='?',
                        default="softmax", help="tensorflow loss")
    parser.add_argument('--iterations', nargs='?', type=int,
                        default=1000, help="training iterations")
    parser.add_argument('--learning_rate', nargs='?', type=float,
                        default=0.01, help="learning rate (0.01)")
    main(parser.parse_args())