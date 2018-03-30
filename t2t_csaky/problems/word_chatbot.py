from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# general imports
import tensorflow as tf
import os

# tensor2tensor imports
from tensor2tensor.data_generators import problem
from tensor2tensor.data_generators import text_problems
from tensor2tensor.data_generators import text_encoder
from tensor2tensor.utils import registry

# Flags
FLAGS = tf.flags.FLAGS

# End-of-sentence marker
EOS = text_encoder.EOS_ID


class WordChatbot(text_problems.Text2TextProblem):
  """
  An abstract base class for word based chatbot problems.
  """

  @property
  def dataset_splits(self):
    return [{
      "split": problem.DatasetSplit.TRAIN,
      "shards": 1,
      "size": 80,
    }, {
      "split": problem.DatasetSplit.EVAL,
      "shards": 1,
      "size": 10,
    }, {
      "split": problem.DatasetSplit.TEST,
      "shards": 1,
      "size": 10,
    }]

  @property
  def is_generate_per_split(self):
    return True

  @property
  def vocab_name(self):
    return "vocab.chatbot"

  @property
  def vocab_type(self):
    return text_problems.VocabType.TOKEN

  @property
  def input_space_id(self):
    return problem.SpaceID.EN_TOK

  @property
  def target_space_id(self):
    return problem.SpaceID.EN_TOK

  @property
  def targeted_vocab_size(self):
    return NotImplementedError

  @property
  def targeted_dataset_size(self):
    # number of utterance pairs in the full dataset
    # if it's 0, then the full size of the dataset is used
    return NotImplementedError

  @property
  def data_dir(self):
    return ""

  @property
  def raw_data_dir(self):
    return ""

  @property
  def raw_data(self):
    return ""

  @property
  def zipped_data(self):
    return ""

  @property
  def url(self):
    return ""

  """ Setter methods for the string properties """
  @data_dir.setter
  def data_dir(self, value):
    self._data_dir=value

  @raw_data_dir.setter
  def raw_data_dir(self, value):
    self._raw_data_dir=value

  @raw_data.setter
  def raw_data(self, value):
    self._raw_data=value

  @zipped_data.setter
  def zipped_data(self, value):
    self._zipped_data=value

  @url.setter
  def url(self, value):
    self._url=value

  # main function where the preprocessing of the data starts
  def preprocess_data(self, train_mode):
    return NotImplementedError

  # This function generates the train and validation pairs in t2t-datagen style
  def generate_samples(self, data_dir, tmp_dir, train):
    """ 
    The function assumes that if you have data at one level of the pipeline, you 
    don't want to re-generate it, so for example if the 4 txt files exist, the function
    continues by generating the t2t-datagen format files, so if you want to re-download
    or re-generate data you have to delete it first from the appropriate directories.

    Params:
      :data_dir:  directory where the data will be generated
                  the raw data has to be downloaded one directory level higher
      :train:     whether we are in train or validation mode
    """

    # determine whether we are in training or validation mode
    if train==problem.DatasetSplit.TRAIN:
      mode="train"
    elif train==problem.DatasetSplit.EVAL:
      mode="dev"
    else:
      mode="test"

    print("t2t_csaky_log: "+mode+" data generation activated.")
    self.data_dir=data_dir
    sourcePath=os.path.join(data_dir, mode+"Source.txt")
    targetPath=os.path.join(data_dir, mode+"Target.txt")

    # create the source and target txt files from the raw data
    self.preprocess_data(mode)

    # create a t2t symbolizer vocab from
    symbolizer_vocab = text_encoder.TokenTextEncoder(os.path.join(data_dir, self.vocab_file),
                                                    num_reserved_ids=0,
                                                    replace_oov="<unk>")

    return self.token_generator(sourcePath,targetPath,symbolizer_vocab, EOS)

  # Generator for sequence-to-sequence tasks that uses tokens.
  def token_generator(self, source_path, target_path, token_vocab, eos=None):
    """
    This generator assumes the files at source_path and target_path have
    the same number of lines and yields dictionaries of "inputs" and "targets"
    where inputs are token ids from the " "-split source (and target, resp.) lines
    converted to integers using the token_map.

    Args:
      source_path: path to the file with source sentences.
      target_path: path to the file with target sentences.
      token_vocab: text_encoder.TextEncoder object.
      eos: integer to append at the end of each sequence (default: None).

    Yields:
      A dictionary {"inputs": source-line, "targets": target-line} where
      the lines are integer lists converted from tokens in the file lines.
    """
    eos_list = [] if eos is None else [eos]
    with tf.gfile.GFile(source_path, mode="r") as source_file:
      with tf.gfile.GFile(target_path, mode="r") as target_file:
        source, target = source_file.readline(), target_file.readline()
        while source and target:
          # try to encode the source and target sentences
          try:
            source_ints = token_vocab.encode(source.strip()) + eos_list
          except KeyError:
            print("t2t_csaky_log: WARNING:COULD NOT BE ENCODED: "+source)
          try:
            target_ints = token_vocab.encode(target.strip()) + eos_list
          except KeyError:
            print("t2t_csaky_log: WARNING:COULD NOT BE ENCODED: "+target)

          yield {"inputs": source_ints, "targets": target_ints}
          source, target = source_file.readline(), target_file.readline()

  # Overwrite the feature encoders, so that I can give my own encoding process
  def feature_encoders(self, data_dir):
    if self.is_character_level:
      encoder=text_encoder.ByteTextEncoder()
    elif self.use_subword_tokenizer:
      vocab_filename=os.path.join(data_dir,self.vocab_file)
      encoder=text_encoder.SubwordTextEncoder(vocab_filename)
    else:
      vocab_filename=os.path.join(data_dir,self.vocab_file)
      encoder=text_encoder.TokenTextEncoder(vocab_filename, replace_oov="<unk>")
    if self.has_inputs:
      return {"inputs":encoder,"targets":encoder}
    return {"targets":encoder}