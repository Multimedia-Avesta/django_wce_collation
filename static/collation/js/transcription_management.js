/*jshint esversion: 6 */
projectSummary = (function () {
    "use strict";

    var _saveProjectWitnesses, _setupPage, showProgressBox, _retrieveDownloadedFile,
    _sortTranscriptionIdentifiers, _showWitnesses, _addHandlers,  _populateTranscriptionDropdowns,
    _readFile, _generateLatex, _resetForm, _downloadTranscription, _extractRitualDirections,
    _extractNotes, _handleError, _showErrorBox;

    var projectData;

  $(document).ready(function () {
    api.setupAjax();
    _setupPage();
    _addHandlers();
  });

  _readFile = function(file_input_id, store_location_id, onload_callback) {
    var store_elem, input_file, reader;
    store_elem = document.getElementById(store_location_id);
    input_file = document.getElementById(file_input_id).files[0];
    reader = new FileReader();
    reader.onloadend = function() {
      store_elem.value = reader.result;
      if (onload_callback) {
        onload_callback();
      }
    };
    if (input_file) {
      reader.readAsDataURL(input_file);
    } else {
      store_elem.value = '';
    }
  };

  _resetForm = function () {
      document.getElementById('get_latex_button').disabled = true;
      document.getElementById('latex_src').value = '';
      document.getElementById('make_latex').value = null;
  };

  _addHandlers = function () {
    $('#extract-notes-button').on('click', function () {
      var data;
      data = forms.serialiseForm('note-extraction-form');
      _extractNotes(data);
    });
    $('#extract-rd-button').on('click', function () {
      var data;
      data = forms.serialiseForm('ritual-direction-extraction-form');
      _extractRitualDirections(data);
    });
    $('#make_latex').off('change.latex');
    $('#make_latex').on('change.latex', function() {
      _readFile('make_latex', 'latex_src', function() {
        document.getElementById('get_latex_button').disabled = false;
        $('#get_latex_button').off('click.latex');
        $('#get_latex_button').on('click.latex', function() {
          var f, data;
          f = document.getElementById('make_latex').files[0];
          data = forms.serialiseForm('get-latex-form');
          data.project_id = document.getElementById('project_id').value;
          _generateLatex(data);
        });
      });
    });
    $('body').on('click', 'button#completed-task-download-button', function () {
      _retrieveDownloadedFile(this.getAttribute('data-url'));
    });
    $('#save-base-text-button').on('click', function () {
      _saveBaseText();
    });
  };

  _generateLatex = function(data) {
      var url, callback;
      url = '/collation/latex/';
      showProgressBox(JSON.stringify({}));
      callback = function (resp) {
        showProgressBox(resp);
        indexing.pollApparatusState();
        _resetForm();
      };
      $.post(url, data, function (response) {
          callback(response);
      }, "text").fail(function (response) {
        _resetForm();
        _handleError('latexgenerator', response);
      });
  };

  _retrieveDownloadedFile = function (url) {
    $.get(url, function (response) {
        console.log(response);
    }).fail(function (response) {
        console.log(response);
    });
  };

  _setupPage = function () {
    var projectId;
    projectId = document.getElementById('project_id').value;
    api.getItemFromDatabasePromise('collation', 'project', projectId).then(function (data) {
      projectData = data;
      _showWitnesses(projectData);
    });
  };

  _extractRitualDirections = function (data) {
    var ritualDirectionsUrl, callback;
    ritualDirectionsUrl = '/collation/ritualdirections';
    showProgressBox(JSON.stringify({}));
    callback = function (resp) {
      showProgressBox(resp);
      indexing.pollApparatusState();
    };
    $.post(ritualDirectionsUrl, data, function(response) {
      callback(response);
    }, "text").fail(function (response) {
      handleError('ritualdirections', response);
    });
  };

  _extractNotes = function (data) {
    var noteUrl, callback;
    noteUrl = '/collation/notes';
    showProgressBox(JSON.stringify({}));
    callback = function (resp) {
      showProgressBox(resp);
      indexing.pollApparatusState();
    };
    $.post(noteUrl, data, function(response) {
      callback(response);
    }, "text").fail(function (response) {
      handleError('notes', response);
    });
  };

  _handleError = function(action, error_report, model) {
    var report;
    report = 'An error has occurred.<br/>';
      if (error_report.status === 401) {
        report += '<br/>You are not authorised to perform this action.<br/>' +
          				'Please contact the server administrator.';
      } else if (error_report.status === 415) {
        report += '<br/>It is has not been possible to process your request because ' +
          				error_report.responseText + '.';
      } else {
        report += '<br/>The server has encountered an error. Please try again. <br/>' +
          				'If the problem persists please contact the server administrator.';
      }
      _showErrorBox(report);
   };

   _showErrorBox = function(report) {
     var error_div;
     if (document.getElementById('error') !== null) {
       document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
     }
     error_div = document.createElement('div');
     error_div.setAttribute('id', 'error');
     error_div.setAttribute('class', 'error_message');
     error_div.innerHTML = '<span id="error_title"><b>Error</b></span>' +
                           '<div id="error_close">close</div><br/><br/>' + report;
     document.getElementsByTagName('body')[0].appendChild(error_div);
     $('#error_close').off('click.error-close');
     $('#error_close').on('click.error-close', function(event) {
       document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
       window.location.reload();
     });
   };

  _saveProjectWitnesses = function(identifiers, basetext, projectId) {
    var data;
    data = {'witnesses': identifiers};
    if (identifiers.indexOf(basetext) === -1) {
      data.basetext = null;
    } else {
      data.basetext = basetext;
    }
    api.updateFieldsInDatabasePromise('collation', 'project', projectId, data).then(function () {
      location.reload();
    });
  };

  showProgressBox = function(data) {
    var message_div;
    data = JSON.parse(data);
    if (document.getElementById('error') !== null) {
      document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
    }
    message_div = document.createElement('div');
    message_div.setAttribute('id', 'error');
    message_div.setAttribute('class', 'message');
    if (data.hasOwnProperty('task_id')) {
        message_div.innerHTML = '<span id="message_title"><b>Task Progress</b></span>' +
                              '<div id="error_close"></div><br/><br/>' +
                              '<input type="hidden" id="task_id" value="' + data.task_id + '"/>' +
                              '<p id="message">Checking the server for the task (' + data.task_id + ').</p>' +
                              '<p id="indicator"></p>';
    } else {
        message_div.innerHTML = '<span id="message_title"><b>Task Progress</b></span>' +
                              '<div id="error_close"></div><br/><br/>' +
                              '<input type="hidden" id="task_id" value=""/>' +
                              '<p id="message">The task is being sent to the server.</p>' +
                              '<p id="indicator"></p>';
    }
    document.getElementsByTagName('body')[0].appendChild(message_div);
  };

  _sortTranscriptionIdentifiers = function (a, b) {
    var siglumA, siglumB;
    siglumA = a.split('_')[1];
    siglumB = b.split('_')[1];
    if (isNaN(parseInt(siglumA))) {
      return -1;
    }
    if (isNaN(parseInt(siglumB))) {
      return 1;
    }
    return parseInt(siglumA) - parseInt(siglumB);
  };

  _showWitnesses = function(projectData) {
    var projectBasetext, projectWitnesses, unavailableProjectWitnesses, projectBasetextIdentifier;

    projectWitnesses = projectData.witnesses;
    projectBasetext = projectData.basetext;
    projectBasetextIdentifier = null;

    api.getItemsFromDatabasePromise('transcriptions', 'transcription', {
      'user__id': projectData.managing_editor,
      'limit': 100000000000,
      '_fields': 'identifier,id'
    }).then(function(transcriptions) {
      var transcriptionsAvailableToAdd, projectBasetextsHTML, transcriptionsUploaded,
      unavailableProjectWitnesses, projectWitnessesHTML, transcriptionsAvailableHTML, baseTextData;

      transcriptionsUploaded = [];
      for (let i=0; i<transcriptions.results.length; i+=1) {
        if (transcriptions.results[i].id === projectData.basetext) {
          projectBasetextIdentifier = transcriptions.results[i].identifier;
        }
        transcriptionsUploaded.push(transcriptions.results[i].identifier);
      }
      transcriptionsAvailableToAdd = transcriptionsUploaded.filter(x => !projectWitnesses.includes(x));
      unavailableProjectWitnesses = projectWitnesses.filter(x => !transcriptionsUploaded.includes(x));
      projectWitnesses.sort(_sortTranscriptionIdentifiers);
      if (document.getElementById('project_witnesses')) {
          projectWitnessesHTML = [];
          for (let i=0; i<projectWitnesses.length; i+=1) {
            if (unavailableProjectWitnesses.indexOf(projectWitnesses[i]) !== -1) {
              projectWitnessesHTML.push('<li id="' + projectWitnesses[i]  + '" class="transcription_missing draggable_item"><input type="hidden" value="' + projectWitnesses[i] + '" name="witness"/>' + projectWitnesses[i] + '</li>');
            } else {
              projectWitnessesHTML.push('<li id="' + projectWitnesses[i]  + '" class="draggable_item"><input type="hidden" value="' + projectWitnesses[i] + '" name="witness"/>' + projectWitnesses[i] + '</li>');
            }
          }
          document.getElementById('project_witnesses').innerHTML = projectWitnessesHTML.join('');

          transcriptionsAvailableToAdd.sort(_sortTranscriptionIdentifiers);
          transcriptionsAvailableHTML = [];
          for (let i=0; i<transcriptionsAvailableToAdd.length; i+=1) {
            transcriptionsAvailableHTML.push('<li id="' + transcriptionsAvailableToAdd[i] + '" class="draggable_item"><input type="hidden" value="' + transcriptionsAvailableToAdd[i] + '" name="witness"/>' + transcriptionsAvailableToAdd[i] + '</li>');
          }
          document.getElementById('additional_witnesses').innerHTML = transcriptionsAvailableHTML.join('');

          forms.populateSelect(projectWitnesses, document.getElementById('base-text-identifier'), {'selected': projectBasetext});

          if (projectWitnesses.length === 0) {
            document.getElementById('basetext-description').innerHTML = 'Before you can select a base text you need to specify the transcriptions for the project below.';
          } else {
            document.getElementById('basetext-description').innerHTML = '';
          }
      }
      _populateTranscriptionDropdowns(projectWitnesses);

      new Sortable(document.getElementById('project_witnesses'), {group: 'witnesses', sort: false, animation: 150});
      new Sortable(document.getElementById('additional_witnesses'), {group: 'witnesses', sort: false,  animation: 150});

        $('#save_witness_selection').on('click', function () {
          var basetext, values = [];
          $('#project_witnesses input[name="witness"]').each(function () {
            values.push(this.value);
          });
          basetext = document.getElementById('base-text-identifier').value;
          _saveProjectWitnesses(values, basetext, projectData.id);
          return false;
        });
    });
  };

  _populateTranscriptionDropdowns = function(projectWitnesses) {
    forms.populateSelect(projectWitnesses, document.getElementById('download-transcription'));
    projectWitnesses.unshift('All project transcriptions');
    forms.populateSelect(projectWitnesses, document.getElementById('extract-notes-from-transcription'), {'add_select': false});
    forms.populateSelect(projectWitnesses, document.getElementById('extract-rd-from-transcription'), {'add_select': false});
    $('#download-transcription-button').off('click');
    $('#download-transcription-button').on('click', function(event) {
      _downloadTranscription(document.getElementById('download-transcription').value);
    });
  };

  _downloadTranscription = function(transcriptionId) {
    if (transcriptionId === 'none') {
      return;
    }
    api.getItemsFromDatabasePromise('transcriptions',
                                    'transcription',
                                    {'identifier': transcriptionId}
                                   ).then(function(transcriptions){
      var a, tei, blob, filename, url;
      if (transcriptions.results.length === 0) {
        alert('No transcription could be found with this identifier.');
        return;
      } else {
        a = document.createElement('a');
        document.body.appendChild(a);
        a.style = 'display: none';
        tei = transcriptions.results[0].tei;
        blob = new Blob([tei], {'type': 'text/xml'});
        filename = transcriptionId + '.xml';
        a.download = filename;
        window.URL = window.URL || window.webkit.url;
        url = window.URL.createObjectURL(blob);
        a.href = url;
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    });
  };

  return {};

} () );
