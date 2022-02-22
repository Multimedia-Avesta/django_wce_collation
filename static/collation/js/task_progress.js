/*jshint esversion: 6 */
indexing = (function () {
    "use strict";

    var pollApparatusState;
    var poll_xhr;


  pollApparatusState = function () {
    var poll, stop;
    stop = false;
    poll = function(){
        var task_id, siglum;
        task_id = document.getElementById('task_id').value;
        poll_xhr = $.ajax({
          url:'../pollstate',
          type: 'POST',
          data: {
              task_id: task_id,
          },
          success: function(result) {
              if (result.state === 'SUCCESS' || result.state === 'FAILURE') {
                  stop = true;
                  if (result.state === 'SUCCESS') {
                      if (Array.isArray(result.result)) {
                          if (result.result[0] === 'download') {
                              document.getElementById('message').innerHTML = 'Your task is complete: <a href="' +
                                                                             result.result[1] + '?file=' +
                                                                             task_id + '">Download</a>';
                              if (document.getElementById('indicator')) {
                                document.getElementById('indicator').innerHTML = '';
                              }
                          } else if (result.result[0] === 'email') {
                              document.getElementById('message').innerHTML = 'Your task is complete and an email has been sent to your registered email address.';
                              if (document.getElementById('indicator')) {
                                document.getElementById('indicator').innerHTML = '';
                              }
                          } else {
                              document.getElementById('message').innerHTML = 'Your task is complete.';
                              document.getElementById('indicator').innerHTML = '';
                          }
                      } else {
                            document.getElementById('message').innerHTML = 'Your task is complete.';
                            document.getElementById('indicator').innerHTML = '';
                      }
                  } else {
                      document.getElementById('message').innerHTML = 'Your task failed with the message:<br/><br/>' +
                                                                     result.result + '<br/><br/>' +
                                                                     'Task Id: ' + task_id;
                      document.getElementById('indicator').innerHTML = '';
                  }
                  document.getElementById('error_close').innerHTML = 'close';
                  $('#error_close').off('click.error-close');
                  $('#error_close').on('click.error-close', function(event) {
                    document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
                    try {
                      transcript_uploader.prepareForm();
                    } catch(err) {

                    }
                  });
              } else if (result.state === 'PENDING') {
                  // We have the flag to tell us when the task has started so pending is a waiting state
                  document.getElementById('message').innerHTML = 'Your task is waiting to start.' +
                                                                 '<br/><br/>Task Id: ' + task_id;
                  document.getElementById('indicator').innerHTML += '.&#8203;';
              } else {
                  document.getElementById('message').innerHTML = 'Your task is in progress.' +
                                                                 '<br/><br/>Task Id: ' + task_id;
                  document.getElementById('indicator').innerHTML += '.&#8203;';
              }
          }
        });
    };
    var refreshIntervalId = setInterval(function() {
        poll();
        if (stop === true) {
            clearInterval(refreshIntervalId);
        }
    }, 500);
  };

  return {pollApparatusState: pollApparatusState};

} () );
