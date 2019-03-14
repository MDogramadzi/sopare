from __future__ import division
import pexpect
from os import listdir
import sys


class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("logfile.log", "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass    

sys.stdout = Logger()


test_folder = "./test_samples/"

learned_words = ["controller", "tv", "power", "volume", "speaker", "up", "down"]

l_arr = [0.0, 1.03, 1.05]
d_arr = [0.01, 0.03, 0.05]
mv_arr = [0.64, 0.68, 0.72, 0.76, 0.8]
mc_arr = [0.64, 0.68, 0.72, 0.76, 0.8]

f1_res = []

for length in l_arr:
    
    for delta in d_arr:

        for mv in mv_arr:

            for mc in mc_arr:

                # every (L,D) pair needs an F1 score
                # for now, just print number of correct/incorrect matches

                # f1 score: 2 x [(precision x recall) / (precision + recall)]
                # precision: true_pos / [true_pos + false_pos]
                # recall: true_pos / [true_pos + false_neg]

                true_pos = 0
                true_neg = 0
                false_pos = 0
                false_neg = 0

                test_files = sorted(listdir(test_folder))
                for test_file in test_files:

                    if ((length == 0.0 and delta != 0.0) or (length == 1.0 and delta == 0.0)):
                        break

                    #print("---------------")
                    #print("Length: " + str(length) + "   " + "Delta: " + str(delta))
                    #print("Input: " + str(test_file))

                    word_label = test_file.split('_')[0]
                    test_file = test_folder + test_file  # prepend test sample folder

                    child = pexpect.spawn("./sopare.py -e {} {} {} {} {}".format(test_file, length, delta, mv, mc))

                    # possible return values are: [], [''], [u'power'], OR [u'power', '...']
                    child.expect('\[.*\]')  # regexp for word match results
                    if child.after == "[]" or child.after == "['']":
                        # if word is a learned word, this is bad
                        # else, this is good
                        if word_label in learned_words:
                            #print(word_label, "Learned word not identified - BAD")
                            false_neg += 1
                        else:
                            #print(word_label, "Random word not identified - GOOD")
                            true_neg += 1
                    else:
                        # check if the returned word matches the input speech command
                        words = child.after.split("'")
                        for i in range(0, len(words)):
                            if (i % 2) != 0:
                                if words[i] == word_label:
                                    #print(words[i], "Correct Match")
                                    true_pos += 1
                                else:
                                    #print(words[i], "Incorrect Match")
                                    false_pos += 1
                    child.close()

                if not ((length == 0.0 and delta != 0.0) or (length == 1.0 and delta == 0.0)):
                    print(length, delta, mv, mc, true_pos, false_pos, false_neg)
                    f1_res.append((length, delta, mv, mc, true_pos, false_pos, false_neg))

print("~~~~~~~~~~~~~~")
for res in f1_res:
    tp, fp, fn = res[4], res[5], res[6]
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    f1_score = 2 * ((precision * recall) / (precision + recall))
    #print("MARGINAL_VAL: " + str(res[0]) + " ... MIN_CROSS_SIM: " + str(res[1]) +  " ... F1 Score: " + str(f1_score))
    print("Length: " + str(res[0]) + " ... Delta: " + str(res[1]) + " ... Marginal Val: " + str(res[2]) + " ...Min Cross: " + str(res[3]) + " ... F1 Score: " + str(f1_score))
print("~~~~~~~~~~~~~~")

