import numpy as np
import pickle 
from extract_features_and_dump import define_model
from rnn_model import hinge_rank_loss
import keras 
from keras.models import Model, load_model 
from keras.layers import Input, Dense, BatchNormalization, Activation, Dropout, Embedding, LSTM, concatenate
import keras.backend as K
from keras.layers import Lambda
import sys, os 
from keras.applications import VGG16
from keras.preprocessing import image
from keras.applications.imagenet_utils import preprocess_input


class FullModel:
	
	def __init__(self, caption, rnn_model_loc):
		# some globals 
		self.WORD_DIM = 300
		self.BATCH = 1 
		
		# fixed caption (to be used against perturbed images to calculate loss)
		self.caption = caption

		assert self.caption.shape == (1,20), "Incorrect shape of captions having shape {}".format(self.caption.shape) 
		assert os.path.isfile(rnn_model_loc), "Provided incorect location to rnn model"

		# vgg16 - fc2 output
		top_model = VGG16(weights="imagenet", include_top="True")
		self.top_model = Model(inputs=top_model.input, outputs=top_model.get_layer("fc2").output)

		# rnn part + recompile with new loss
		self.rnn_model = load_model(rnn_model_loc, custom_objects={"hinge_rank_loss":hinge_rank_loss})
		self.rnn_model.compile(optimizer="rmsprop", loss=self.custom_distance_function)

	def custom_distance_function(self, y_true, y_pred):

		select_images = lambda x: x[:, :self.WORD_DIM]
		select_words = lambda x: x[:, self.WORD_DIM:]

		slice_first = lambda x: x[0:1 , :]

		# separate the images from the captions==words
		image_vectors = Lambda(select_images, output_shape=(self.BATCH, self.WORD_DIM))(y_pred)
		word_vectors = Lambda(select_words, output_shape=(self.BATCH, self.WORD_DIM))(y_pred)

		# separate correct/wrong images
		correct_image = Lambda(slice_first, output_shape=(1, self.WORD_DIM))(image_vectors)

		# separate correct/wrong words
		correct_word = Lambda(slice_first, output_shape=(1, self.WORD_DIM))(word_vectors)

		# l2 norm
		l2 = lambda x: K.sqrt(K.sum(K.square(x), axis=1, keepdims=True))
		l2norm = lambda x: x/l2(x)
		
		correct_image = l2norm(correct_image)
		correct_word = l2norm(correct_word)

		# correct_image VS incorrect_words | Note the singular/plurals
		cost_images = K.sum(correct_image * correct_word, axis=1)
		cost_images = K.sum(cost_images, axis=-1)

		return cost_images ## WAS EARLIER DIVIDING BY INCORRECT_self.BATCH WHICH HAS BEEN SET TO 0, IDIOT.

	def predict(self, x):

		# checks
		assert x.shape == (1, 3, 224, 224), "Incorrect input dims of {}".format(x.shape) 

		# pass through vgg 
		top_op = self.top_model.predict(x)

		# pass through rnn model (get loss) 
		loss = self.rnn_model.test_on_batch([top_op, self.caption], np.zeros(1))

		return loss

	
def TEST():
	cap_input = np.array([[8, 214, 23, 1, 626, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])
	img_input = image.load_img("/Users/tejaswin.p/Downloads/eating_pizza_in_park.jpg", target_size=(224, 224))
	x = image.img_to_array(img_input)
	x = np.expand_dims(x, axis=0)
	x = preprocess_input(x)
    
	model = FullModel(cap_input, "/Users/tejaswin.p/Downloads/epoch_9.hdf5")
	print "CORRECT caption similarity:", model.predict(x)

	model.caption = np.array([[8, 199, 23, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])
	print "RANDOM caption similarity:", model.predict(x)

	K.clear_session()

if __name__ == '__main__':
	TEST()
		