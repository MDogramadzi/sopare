var util = require('util');

var bleno = require('./node_modules/bleno/index');

var fs = require('fs');



var BlenoPrimaryService = bleno.PrimaryService;
var BlenoCharacteristic = bleno.Characteristic;
var BlenoDescriptor = bleno.Descriptor;


// Reading Trained Words
var ReadTrainedWords = function() {
  ReadTrainedWords.super_.call(this, {
    uuid: 'fffffffffffffffffffffffffffffff1',
    properties: ['read']
  });
};

util.inherits(ReadTrainedWords, BlenoCharacteristic);

ReadTrainedWords.prototype.onReadRequest = function(offset, callback) {
  var result = this.RESULT_SUCCESS;

  // get list of trained words from the dict directory

  fs.readdir("./dict", function (err, files)  {
    if (err)  {
      console.log("Could not list directory: ", err);
      callback(result, "")
      return
    }

    var fileCount = files.length - 1;
    var fileCounter = 0;
    var allWords = [];

    files.forEach(function (file, index)  {
        var fileExt = file.split('.')[1];
        if (fileExt === "raw")  {
            fs.readFile("./dict/"+file, {encoding: 'utf-8'}, function(err,data) {
                if (err)  {
                    console.log(err);
                }
                else  {
                    var file = JSON.parse(data);
                    if (!allWords.includes(file["id"]))  {
                        allWords.push(file["id"])
                    }
                }
                fileCounter += 1;
                if (fileCounter == fileCount)  {
                    var finalString = "";
                    for (var i = 0; i < allWords.length; i++)  {
                        finalString += allWords[i] + "-"
                    }
                    if (finalString != "")  {
                        finalString = finalString.slice(0, -1);
                    }

                    console.log(finalString);

                    var data = new Buffer(finalString);

                    if (offset > data.length) {
                        result = this.RESULT_INVALID_OFFSET;
                        data = null;
                    } else {
                        data = data.slice(offset);
                    }

                    callback(result, data);
                }
            });
        }
    });

  });

};


// Reading Command List
var ReadCommandList = function() {
  ReadCommandList.super_.call(this, {
    uuid: 'fffffffffffffffffffffffffffffff2',
    properties: ['read']
  });
};

util.inherits(ReadCommandList, BlenoCharacteristic);

ReadCommandList.prototype.onReadRequest = function(offset, callback) {
  var result = this.RESULT_SUCCESS;

  var ir_map = fs.readFileSync('./ir_map.json', 'utf8');
  console.log(ir_map.toString());
  var data = new Buffer(ir_map.toString());

  if (offset > data.length) {
    result = this.RESULT_INVALID_OFFSET;
    data = null;
  } else {
    data = data.slice(offset);
  }

  callback(result, data);
};


// Calling Procedures using Writes
var CallProcedure = function() {
  CallProcedure.super_.call(this, {
    uuid: 'fffffffffffffffffffffffffffffff4',
    properties: ['write', 'writeWithoutResponse']
  });
};

util.inherits(CallProcedure, BlenoCharacteristic);

CallProcedure.prototype.onWriteRequest = function(data, offset, withoutResponse, callback) {
  console.log('Writing: ' + data.toString('utf8'));

  callback(this.RESULT_SUCCESS);
};


// Service Instantiation
function SampleService() {
  SampleService.super_.call(this, {
    uuid: 'fffffffffffffffffffffffffffffff0',
    characteristics: [
      new ReadTrainedWords(),
      new ReadCommandList(),
      new CallProcedure()
    ]
  });
}

util.inherits(SampleService, BlenoPrimaryService);


bleno.on('stateChange', function(state) {
  console.log('on -> stateChange: ' + state + ', address = ' + bleno.address);

  if (state === 'poweredOn') {
    bleno.startAdvertising('test', ['fffffffffffffffffffffffffffffff0']);
  } else {
    bleno.stopAdvertising();
  }
});

// Linux only events /////////////////
bleno.on('accept', function(clientAddress) {
  console.log('on -> accept, client: ' + clientAddress);

  bleno.updateRssi();
});

bleno.on('disconnect', function(clientAddress) {
  console.log('on -> disconnect, client: ' + clientAddress);
});

bleno.on('rssiUpdate', function(rssi) {
  console.log('on -> rssiUpdate: ' + rssi);
});
//////////////////////////////////////

bleno.on('mtuChange', function(mtu) {
  console.log('on -> mtuChange: ' + mtu);
});

bleno.on('advertisingStart', function(error) {
  console.log('on -> advertisingStart: ' + (error ? 'error ' + error : 'success'));

  if (!error) {
    bleno.setServices([
      new SampleService()
    ]);
  }
});

bleno.on('advertisingStop', function() {
  console.log('on -> advertisingStop');
});

bleno.on('servicesSet', function(error) {
  console.log('on -> servicesSet: ' + (error ? 'error ' + error : 'success'));
});

