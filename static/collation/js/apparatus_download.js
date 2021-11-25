/*jshint esversion: 6 */
apparatusDownload = (function () {
    "use strict";

    var pollApparatusState;
    var stop = 0;
    var poll_xhr;

  $(document).ready(function () {
    api.setupAjax();
    pollApparatusState();
  });

  pollApparatusState = function () {
    var poll;
    poll = function(){
        var task_id = document.getElementById('task_id').value;
        poll_xhr = $.ajax({
          url:'../pollstate',
          type: 'POST',
          data: {
              task_id: task_id,
          },
          success: function(result) {
              if (result.state === 'SUCCESS' || result.state === 'FAILURE') {
                  stop = 1;
                  if (result.state === 'SUCCESS') {
                      document.getElementById('user-count').innerHTML = 'Your task is complete: <a href="?file=' + task_id + '">Download</a>';
                      if (result.result[2].length > 0) {
                        document.getElementById('errors').innerHTML = 'Errors:<br/>' + '<br/>'.join(result.result[2]);
                      }
                  } else {
                      document.getElementById('user-count').textContent = 'Your task (' + task_id + ') failed.';
                  }
              } else {
                  document.getElementById('user-count').textContent = 'Your task (' + task_id + ') is running.';
              }
          }
        });
    };
    var refreshIntervalId = setInterval(function() {
        poll();
        if(stop == 1){
            clearInterval(refreshIntervalId);
        }
    }, 500);
  };




} () );
