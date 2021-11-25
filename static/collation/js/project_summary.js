/*jshint esversion: 6 */
projectSummary = (function () {
    "use strict";

    var _loadProjectSummary, _saveProjectWitnesses, _caculateProgress, _displayProgress, showProgressBox,
    _addHandlers, _setDefaults, _addDeleteFunctions, _getDetails, _constructDetailsTable, _handleError,
    showSummaryLoadingOverlay;
    var excludedList = [], omitApparatusList = [], projectData;
    var excludedCount = 0;
    var omitApparatusCount = 0;

  $(document).ready(function () {
    api.setupAjax();
    _loadProjectSummary();
    _setDefaults();
    _addHandlers();
  });

  _setDefaults = function () {
    document.getElementById('apparatus_select').value = 'include';
    document.getElementById('chapter_export_select').value = 'all';
  };

  _addHandlers = function () {
    $('#summary_selection').on('change', function () {
      var chapter;
      chapter = document.getElementById('summary_selection').value;
      if (chapter === 'all') {
        $('#get-details-button').attr('disabled', true);
        document.getElementById('detail-display').style.display = 'none';
        _caculateProgress(projectData);
      } else {
        $('#get-details-button').removeAttr('disabled');
        _caculateProgress(projectData, chapter);
      }
    });
    $('#get-details-button').on('click', function () {
      $('#detail-display').toggle();
    });
    $('#add_excluded').on('click', function () {
      var value, li;
      value = document.getElementById('excluded_units_select').value;
      if (value != 'none') {
        if (excludedList.indexOf(value) == -1) {
          excludedList.push(value);
          excludedCount += 1;
          li = document.createElement('li');
          li.setAttribute('data-value', value);
          li.innerHTML = value + '<input type="hidden" value="' + value + '" name="excluded_' + excludedCount +'"/>' +
                        '<img  alt="delete logo" class="delete_exclude_unit" src="' + staticUrl + '/collation/images/delete.png"/>';
          document.getElementById('excluded_list').appendChild(li);
          _addDeleteFunctions();
        }
      }
      document.getElementById('excluded_units_select').value = 'none';
    });
    $('#add_omit_apparatus').on('click', function () {
      var value, li;
      value = document.getElementById('exclude_apparatus_select').value;
      if (value != 'none') {
        if (omitApparatusList.indexOf(value) == -1) {
          omitApparatusList.push(value);
          omitApparatusCount += 1;
          li = document.createElement('li');
          li.setAttribute('data-value', value);
          li.innerHTML = value + '<input type="hidden" value="' + value + '" name="omit_apparatus_' +
                         omitApparatusCount + '"/>' +
                         '<img alt="delete logo" class="delete_omit_apparatus" src="' + staticUrl + '/collation/images/delete.png"/>';
          document.getElementById('omit_apparatus_list').appendChild(li);
          _addDeleteFunctions();
        }
      }
      document.getElementById('exclude_apparatus_select').value = 'none';
    });
    $('#get-apparatus-button').on('click', function () {
      var data, apparatusUrl, callback;
      data = forms.serialiseForm('apparatus-output-form');
      apparatusUrl = '/collation/apparatus';
      callback = function (resp) {
        showProgressBox(resp);
        indexing.pollApparatusState();
      };
      $.post(apparatusUrl, data, function(response) {
        callback(response);
      }, "text").fail(function (response) {
        handleError('apparatus', response);
      });
    });
    $('#apparatus-select').on('change', function (e) {
      if (e.target.value === 'include') {
        $('#exclude-apparatus-units').removeClass('disabled');
        document.getElementById('exclude_apparatus_select').removeAttribute('disabled');
        document.getElementById('add_omit_apparatus').removeAttribute('disabled');
      } else if (e.target.value === 'exclude') {
        $('#exclude-apparatus-units').addClass('disabled');
        document.getElementById('exclude_apparatus_select').setAttribute('disabled', 'disabled');
        document.getElementById('add_omit_apparatus').setAttribute('disabled', 'disabled');
      }
    });
    $('#chapter').on('change', function (e) {
      var criteria, chapter;
      chapter = e.target.value;
      if (chapter === 'all') {
        criteria = {'project__id': document.getElementById('project__id').value,
                    'status': 'approved',
                    'limit': 100000000000,
                    '_fields': 'status,context'};
        api.getItemsFromDatabasePromise('collation', 'collation', criteria).then(function (response) {
          var options = {'value_key': 'context', 'text_keys': 'context', 'add_select': true};
          forms.populateSelect(response.results, document.getElementById('excluded_units_select'), options);
          forms.populateSelect(response.results, document.getElementById('exclude_apparatus_select'), options);
        });
      } else {
        criteria = {'project__id': document.getElementById('project__id').value,
                    'status': 'approved',
                    'chapter_number': chapter,
                    'limit': 100000000000,
                    '_fields': 'status,context'};
        api.getItemsFromDatabasePromise('collation', 'collation', criteria).then(function (response) {
          var options = {'value_key': 'context', 'text_keys': 'context', 'add_select': true};
          forms.populateSelect(response.results, document.getElementById('excluded_units_select'), options);
          forms.populateSelect(response.results, document.getElementById('exclude_apparatus_select'), options);
        });
      }
    });
  };

  showProgressBox = function(data) {
    var error_div;
    data = JSON.parse(data);
    $('#check_ingested_data').off('click');
    $('#check_ingested_data').on('click', function() {
      window.location.href = '/transcriptions/collationunits/?siglum=' + data.siglum;
    });
    if (document.getElementById('error') !== null) {
      document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
    }
    error_div = document.createElement('div');
    error_div.setAttribute('id', 'error');
    error_div.setAttribute('class', 'message');
    error_div.innerHTML = '<span id="message_title"><b>Apparatus Progress</b></span>' +
                          '<div id="error_close"></div><br/><br/>' +
                          '<input type="hidden" id="task_id" value="' + data.task_id + '"/>' +
                          '<p id="message">Checking the server for the task (' + data.task_id + ').</p>' +
                          '<p id="indicator"></p>';
    document.getElementsByTagName('body')[0].appendChild(error_div);
  };

  _handleError = function(action, error_report, model) {
    // var report;
    // report = 'An error has occurred.<br/>';
    // if (error_report.status === 401) {
    //   report += '<br/>You are not authorised to upload transcriptions into the database.<br/>' +
    //             'Please contact the server administrator.';
    // } else if (error_report.status === 403) {
    //   if (error_report.responseText == 'work does not match project') {
    //     report += '<br/>You need to select the correct project for the transcription you are uploading.<br/>' +
    //               'Please select a different project and try again.';
    //   } else if (error_report.responseText == 'project is not public') {
    //     report += '<br/>You cannot upload a transcription with the public flag unless the project select is also public.<br/>' +
    //               'Please select a different project or choose the private option and try again.';
    //   } else {
    //     report += '<br/>You are not authorised to upload transcriptions into the database.<br/>' +
    //               'Please contact the server administrator.';
    //   }
    // } else if (error_report.status === 415) {
    //   report += '<br/>It is has not been possible to process your request because ' +
    //             error_report.responseText + '.';
    // } else {
    //   report += '<br/>The server has encountered an error. Please try again. <br/>' +
    //             'If the problem persists please contact the server administrator.';
    // }
    // showErrorBox(report);
  };

  _addDeleteFunctions = function () {
    $('.delete_exclude_unit').off('click');
    $('.delete_exclude_unit').on('click', function (e) {
      var parent, value, index;
      parent = e.target.parentElement;
      value = parent.getAttribute('data-value');
      index = excludedList.indexOf(value);
      document.getElementById('excluded_list').removeChild(parent);
      if (index !== -1) {
        excludedList.splice(index, 1);
      }
    });
    $('.delete_omit_apparatus').off('click');
    $('.delete_omit_apparatus').on('click', function (e) {
      var parent, value, index;
      parent = e.target.parentElement;
      value = parent.getAttribute('data-value');
      index = omitApparatusList.indexOf(value);
      document.getElementById('omit_apparatus_list').removeChild(parent);
      if (index !== -1) {
        omitApparatusList.splice(index, 1);
      }
    });
  };


  _loadProjectSummary = function () {
    var projectId;
    projectId = document.getElementById('project_id').value;
    api.getItemFromDatabasePromise('collation', 'project', projectId).then(function (data) {
      projectData = data;
      document.getElementById('summary_selection').value = 'all';
      $('#get-details-button').attr('disabled', true);
      _caculateProgress(projectData);
    });
  };

  _saveProjectWitnesses = function(identifiers, basetext, projectId) {
    var data;
    data = {'witnesses': identifiers};
    if (basetext !== undefined) {
      data.basetext = basetext;
    }
    api.updateFieldsInDatabasePromise('collation', 'project', projectId, data).then(function () {
      location.reload();
    });
  };

  _getDetails = function (units, details) {
    var levels = ['regularised', 'set', 'ordered', 'approved', 'edited'];
    for (let i=0; i<units.results.length; i+=1) {
      if (details.hasOwnProperty(units.results[i].context)){
        if (units.results[i].last_modified_time !== null) {
          details[units.results[i].context][levels.indexOf(units.results[i].status)] = units.results[i].last_modified_time;
        } else {
          if (units.results[i].created_time !== null) {
            details[units.results[i].context][levels.indexOf(units.results[i].status)] = units.results[i].created_time;
          } else {
            details[units.results[i].context][levels.indexOf(units.results[i].status)] = true;
          }
        }
      }
    }
    return details;
  };

  showSummaryLoadingOverlay = function () {
      document.getElementById('summary_overlay').style.width = document.getElementById('progress_summary_container').clientWidth + 'px';
      document.getElementById('summary_overlay').style.height = document.getElementById('progress_summary_container').clientHeight + 'px';
      document.getElementById('summary_overlay').style.display = 'block';
      document.getElementById('spinner').style.display = 'block';
  };

  _caculateProgress = function (projectData, chapter) {
    var expectedUnitsCriteria, details;
    showSummaryLoadingOverlay();
    details = {};
    expectedUnitsCriteria = {'transcription_identifier': projectData.basetext, 'limit': 100000000000, '_fields': 'transcription_identifier,context'};
    if (chapter !== undefined) {
      expectedUnitsCriteria.chapter_number = chapter;
    }
    api.getItemsFromDatabasePromise('transcriptions', 'collationunit', expectedUnitsCriteria).then(function (units) {
      var totalUnits, unitCriteria;
      totalUnits = units.count;
      if (chapter != undefined) {
        for (let i=0; i<units.results.length; i+=1) {
          details[units.results[i].context] = [null, null, null, null, null];
        }
      }
      unitCriteria = {'project__id': projectData.id, 'user__id': projectData.managing_editor, 'limit': 100000000000, '_fields': 'status,context,created_time,last_modified_time'};
      if (chapter !== undefined) {
        unitCriteria.chapter_number = chapter;
      }
      api.getItemsFromDatabasePromise('collation', 'collation', unitCriteria).then(function (collations) {
        var approvedCriteria;
        approvedCriteria = {'project__id': projectData.id, 'status': 'approved', 'limit': 100000000000, '_fields': 'status,context,created_time,last_modified_time'};
        if (chapter !== undefined) {
          approvedCriteria.chapter_number = chapter;
        }
        api.getItemsFromDatabasePromise('collation', 'collation', approvedCriteria).then(function (approved) {
          var editedCriteria;
          editedCriteria = {'project__id': projectData.id, 'status': 'edited', 'limit': 100000000000, '_fields': 'status,context,created_time,last_modified_time'};
          if (chapter !== undefined) {
            editedCriteria.chapter_number = chapter;
          }
          api.getItemsFromDatabasePromise('collation', 'collation', editedCriteria).then(function (edited) {
            var status, counts;
            counts = {'regularised': 0, 'set': 0, 'ordered': 0, 'approved': 0, 'edited': 0};
            for (let i=0; i<collations.results.length; i+=1) {
              status = collations.results[i].status;
              counts[status] += 1;
            }
            counts.approved = approved.count;
            counts.edited = edited.count;
            if (chapter != undefined) {
              details = _getDetails(collations, details);
              details = _getDetails(approved, details);
              details = _getDetails(edited, details);
            }
            _displayProgress(counts, totalUnits, details);
            document.getElementById('summary_overlay').style.display = 'none';
          });
        });
      });
    });
  };

  _constructDetailsTable = function(details) {
    var html, date, minutes, datestring;
    html = [];
    html.push('<table><tbody>');
    html.push('<tr><th>Siglum</th><th>Regularised</th><th>Set</th><th>Ordered</th><th>Approved</th><th>Text Selected</th></tr>');
    for (let key in details) {
      html.push('<tr>');
      html.push('<td>' + key + '</td>');
      for (let i=0; i<details[key].length; i+=1) {
        if (details[key][i] === null) {
          html.push('<td></td>');
        } else {
          date = new Date(details[key][i]);
          if (date.getMinutes() < 10) {
            minutes = '0' + date.getMinutes();
          } else {
            minutes = String(date.getMinutes());
          }
          datestring = date.getDate() + '/' + (date.getMonth() + 1) + '/' + date.getFullYear() + ' ' + date.getHours() + ':' + minutes;
          html.push('<td>' + datestring + '</td>');
        }
      }
      html.push('</tr>');
    }
    html.push('</tbody></table>');
    document.getElementById('detail-display').innerHTML = html.join('');
  };

  _displayProgress = function (stageCounts, totalUnits, details) {
    var levels, complete, percent;
    levels = ['regularised', 'set', 'ordered', 'approved', 'edited'];
    _constructDetailsTable(details);
    for (let i = 0; i < levels.length; i += 1) {
      complete = stageCounts[levels[i]];
      percent = Math.floor(complete / totalUnits * 100);
      document.getElementById(levels[i] + '_progress').innerHTML = complete;
      document.getElementById(levels[i] + '_total').innerHTML = totalUnits;
      document.getElementById(levels[i] + '_percentage').innerHTML = percent;
      document.getElementById(levels[i] + '_bar').style.width = percent + 'px';
    }
  };

  return {};

} () );
