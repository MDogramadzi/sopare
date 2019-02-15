import pexpect

test_folder = "./test_samples/"

test_files = ["power_1"]

l_arr = [0.25, 0.5, 0.75, 1, 1.25, 1.5]
d_arr = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]

for length in l_arr:
    for delta in d_arr:

        for test_file in test_files:

            word_label = test_file.split('_')[0]
            test_file = test_folder + test_file  # prepend test sample folder

            child = pexpect.spawn("./sopare.py -e {} {} {}".format(test_file, length, delta))

            # possible return values are: [], [''], [u'power'], etc.
            child.expect('\[.*\]')  # regexpt for word match results
            if child.after == "[]" or child.after == "['']":
                print("No match")
            else:
                # check if the returned word matches the input speech command
                word = child.after[3:-2]
                if word == word_label:
                    print(word, "Correct Match")
                else:
                    print(word, "Incorrect Match")

