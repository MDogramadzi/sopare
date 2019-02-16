import pexpect

test_folder = "./test_samples/"

test_files = ["controller_1", "controller_2", "controller_3", "controller_4", "controller_5"]

l_arr = [0.0, 1.01, 1.02, 1.03, 1.04, 1.05]
d_arr = [0.0, 0.01, 0.02, 0.03, 0.04, 0.05]

f1_res = []

for length in l_arr:
    for delta in d_arr:

        # every (L,D) pair needs an F1 score
        # for now, just print number of correct/incorrect matches

        correct_matches = 0
        incorrect_matches = 0

        for test_file in test_files:

            if ((length == 0.0 and delta != 0.0) or (length == 1.0 and delta == 0.0)):
                break

            print("---------------")
            print("Length: " + str(length) + "   " + "Delta: " + str(delta))
            print("Input: " + str(test_file))

            word_label = test_file.split('_')[0]
            test_file = test_folder + test_file  # prepend test sample folder

            child = pexpect.spawn("./sopare.py -e {} {} {}".format(test_file, length, delta))

            # possible return values are: [], [''], [u'power'], OR [u'power', '...']
            child.expect('\[.*\]')  # regexp for word match results
            if child.after == "[]" or child.after == "['']":
                print("No match")
            else:
                # check if the returned word matches the input speech command
                words = child.after.split("'")
                for i in range(0, len(words)):
                    if (i % 2) != 0:
                        if words[i] == word_label:
                            print(words[i], "Correct Match")
                            correct_matches += 1
                        else:
                            print(words[i], "Incorrect Match")
                            incorrect_matches += 1
            child.close()

        if not ((length == 0.0 and delta != 0.0) or (length == 1.0 and delta == 0.0)):
            f1_res.append((length, delta, correct_matches, incorrect_matches))

print("~~~~~~~~~~~~~~")
for res in f1_res:
    print("Length: " + str(res[0]) + " ... Delta: " + str(res[1]) +  " ... Correct: " + str(res[2]) + " ... Incorrect: " + str(res[3]))
print("~~~~~~~~~~~~~~")

