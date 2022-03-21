/*jshint esversion: 6 */
django_services = (function() {
  //TODO: transcription_id in verse data needs to be deprecated in favour of transcription
  //because that is how it is stored in our data now

    const localCollationFunction = {
        'python_file': 'collation.local_collation',
        'class_name': 'LocalCollation',
        'function': 'do_collate'
    };

  const undoStackLength = 12;

  const allowWitnessChangesInSavedCollations = false;

  const supportedRuleScopes = {
            'once': 'This place, these MSS',
	    			'verse': 'This unit, all MSS',
	    			'manuscript': 'Everywhere, these MSS',
	    			'always': 'Everywhere, all MSS'};

  const localJavascript = [staticUrl + 'api/js/api.js',
                            staticUrl + 'collation/js/muya_implementations.js'];

  const contextInput = { //this is only a partial implementation as form itself is handled by Django
       'form' : null,
       'result_provider' : function () {
           var book, chapter, stanza, line, ref;
           book = document.getElementById('book').value;
           chapter = document.getElementById('chapter').value;
           stanza = document.getElementById('stanza').value;
           line = document.getElementById('line').value;
           if (book !== 'none' && !CL.isBlank(chapter) && !CL.isBlank(stanza) && !CL.isBlank(line)) {
               ref = book + '.' + chapter + '.' + stanza + '.' + line;
           }
           return ref;

       }
   };

   const witnessSort = function (witnesses) {
	    return witnesses.sort(LOCAL.sort_witnesses);
	 };

   const prepareDisplayString = function (string) {
     return LOCAL.prepareDisplayString(string); //nothing needed for this project but it is for Greek it should replace _ with underdot
   };

   const prepareNormalisedString = function (string) {
     return LOCAL.prepareDisplayString(string); //nothing needed for this project but it is for Greek it should replace underdot with _
   };

   const combineAllLacsInOR = false;
   const combineAllOmsInOR = false;
   const combineAllLacsInApproved = false;
   const combineAllOmsInApproved = true;

   const lac_unit_label = 'lac unit';
   const om_unit_label = 'om unit';

   const preStageChecks = {
	    "order_readings": [
        	{
        	   "function": "LOCAL.are_no_duplicate_statuses",
        	   "pass_condition": true,
        	   "fail_message": "You cannot move to order readings while there are duplicate overlapped readings"
        	},
        	{
        	   "function": "LOCAL.check_om_overlap_problems",
        	   "pass_condition": false,
        	   "fail_message": "You cannot move to order readings because there is a overlapped reading with the status 'overlapped' that has text in the overlapped unit"
        	},
	    ],
	    "approve": [
	        {
	            "function": "LOCAL.are_no_disallowed_overlaps",
	            "pass_condition": true,
	            "fail_message": "You cannot approve this verse because it has an overlapped reading which is identical in word range to a main apparatus unit."
	        }
	    ]
	};

  const exporterSettings = {"python_file": 'collation.latex_exporter',
                            "class_name": 'LatexExporter',
                            "function": 'export_data',
                            "ignore_basetext": true,
                            'format': 'txt'
                           };


  const overlappedOptions = [{
	    "id": "show_as_overlapped",
	    "label": "Show as overlapped",
	    "reading_flag": "overlapped",
	    "reading_label": "zu",
	    "reading_label_display": "↑"
	},
	{
	    "id": "delete_reading",
	    "label": "Delete reading",
	    "reading_flag": "deleted",
	    "reading_label": "zu",
	}];

	const displaySettings = {
            "python_file": "collation.muya_implementations",
            "class_name": "ApplySettings",
            "configs": [
                {
                    "id": "view_supplied",
                    "label": "view supplied text",
                    "function": "hide_supplied_text",
                    "menu_pos": 1,
                    "execution_pos": 5,
                    "check_by_default": true,
                    "apply_when": false
                },
                {
                    "id": "view_unclear",
                    "label": "view unclear text",
                    "function": "hide_unclear_text",
                    "menu_pos": 2,
                    "execution_pos": 4,
                    "check_by_default": true,
                    "apply_when": false
                },
                {
                    "id": "view_capitalisation",
                    "label": "view capitalisation",
                    "function": "lower_case",
                    "menu_pos": 4,
                    "execution_pos": 3,
                    "check_by_default": false,
                    "apply_when": false
                },
                {
                    "id": "use_lemma",
                    "function": "select_lemma",
                    "menu_pos": null,
                    "execution_pos": 1,
                    "check_by_default": true,
                    "apply_when": true
                },
                {
                    "id": "expand_abbreviations",
                    "label": "expand abbreviations",
                    "function": "expand_abbreviations",
                    "menu_pos": 3,
                    "execution_pos": 2,
                    "check_by_default": false,
                    "apply_when": true
                },
                {
                    "id": "show_punctuation",
                    "label": "show punctuation",
                    "function": "show_punctuation",
                    "menu_pos": 5,
                    "execution_pos": 6,
                    "check_by_default": false,
                    "apply_when": true
                }
            ]
        };

        var ruleClasses = [
          {
            "value": "none",
            "name": "None",
            "create_in_RG": true,
            "create_in_SV": true,
            "create_in_OR": true,
            "suffixed_sigla": false,
            "suffixed_label": false,
            "suffixed_reading": false,
            "subreading": false,
            "keep_as_main_reading": false
          },
         {
            "value": "reconstructed",
            "name": "Reconstructed",
            "create_in_RG": true,
            "create_in_SV": true,
            "create_in_OR": true,
            "identifier": "r",
            "suffixed_sigla": false,
            "suffixed_label": true,
            "suffixed_reading": false,
            "subreading": true,
            "keep_as_main_reading": false
         },
         {
           "value": "orthographic",
           "name": "Orthographic",
           "create_in_RG": true,
           "create_in_SV": true,
           "create_in_OR": true,
           "identifier": "o",
           "suffixed_sigla": false,
           "suffixed_label": true,
           "suffixed_reading": false,
           "subreading": true,
           "keep_as_main_reading": false
          },
          {
            "value": "phonetic",
            "name": "Phonetic",
            "create_in_RG": true,
            "create_in_SV": true,
            "create_in_OR": true,
            "identifier": "p",
            "suffixed_sigla": false,
            "suffixed_label": true,
            "suffixed_reading": false,
            "subreading": true,
            "keep_as_main_reading": false
           },
           {
             "value": "orthographic_phonetic",
             "name": "Orthographic/Phonetic",
             "create_in_RG": true,
             "create_in_SV": true,
             "create_in_OR": true,
             "identifier": "op",
             "suffixed_sigla": false,
             "suffixed_label": true,
             "suffixed_reading": false,
             "subreading": true,
             "keep_as_main_reading": false
            },
          {
            "value": "abbreviation",
            "name": "Abbreviation",
            "create_in_RG": true,
            "create_in_SV": true,
            "create_in_OR": true,
            "suffixed_sigla": false,
            "suffixed_label": false,
            "suffixed_reading": false,
            "subreading": true,
            "keep_as_main_reading": false
          }
        ];

    const ruleConditions = {
        "python_file": "collation.muya_implementations",
        "class_name": "RuleConditions",
        "configs" : [
            {
                "id": "ignore_supplied",
                "label": "Ignore supplied markers",
                "linked_to_settings": true,
                "setting_id": "view_supplied",
                "function": "ignore_supplied",
                "apply_when": true,
                "check_by_default": false,
                "type": "string_application"
            },
            {
                "id": "ignore_unclear",
                "label": "Ignore unclear markers",
                "linked_to_settings": true,
                "setting_id": "view_unclear",
                "function": "ignore_unclear",
                "apply_when": true,
                "check_by_default": false,
                "type": "string_application"
            }
        ]
    };

    const extraFooterButtons = {
      "regularised": [
         {
           "id": "show_ritual_directions",
           "label": "Show/hide ritual directions"
         }
       ],
     "set": [
        {
          "id": "show_ritual_directions",
          "label": "Show/hide ritual directions"
        }
      ],
     "ordered": [
        {
          "id": "show_ritual_directions",
          "label": "Show/hide ritual directions"
        }
      ],
     "approved": [
        {
          "id": "show_ritual_directions",
          "label": "Show/hide ritual directions"
        }
      ]
    };

  //function called on document ready
  $(function () {
    if (typeof patristicsEditor === 'undefined') {
      CL.setServiceProvider(django_services);
    }
  });

  getUserInfo = function (success_callback) {
    api.getCurrentUser(function (response) {
      if (success_callback !== undefined) {
        success_callback(response);
      }
    });
	};

  //TODO: this may no longer be compulsory if we can use 'container' as the default
  initialiseEditor = function () {
    api.setupAjax();
    CL.addIndexHandlers();
    getCurrentEditingProject(function (project) {
      getUserInfo(function (user) {
        if (project.managing_editor == user.id) {
          CL.managingEditor = true;
        } else {
          CL.managingEditor = false;
        }
      });
    });
  };

  showLoginStatus = function(callback) {
    var elem, login_status_message;
    elem = document.getElementById('login_status');
    if (elem !== null) {
      CL.services.getUserInfo(function(response) {
        if (response) {
          //TODO: use data from Profile here? make sure it is insynch with the homepage done by the django template
          login_status_message = 'logged in as ' + response.username;
          elem.innerHTML = login_status_message + '<br/><a href="/accounts/logout?next=/collation">logout</a>';
        } else {
          elem.innerHTML = '<br/><a href="/accounts/login?next=/collation">login</a>';
        }
        if (callback) callback();
      });
    }
  };

  //TODO: projectId settings from CL.project as well as the form element new in 2.0.0
  getCurrentEditingProject = function(success_callback) {
    var projectId;
    if (CL.project.hasOwnProperty('id')) {
      projectId = CL.project.id;
    } else {
      projectId = document.getElementById('project').value;
    }
    api.getItemFromDatabase('collation', 'project', projectId, undefined, function(project) {
      if (project.configuration !== null) {
        for (let key in project.configuration) {
          if (project.configuration.hasOwnProperty(key)) {
            project[key] = project.configuration[key];
          }
        }
      }
      delete project.configuration;
      if (success_callback) {
        success_callback(project);
      }
    });
  };

  //WARNING: this returns only the specified fields which are fine for current uses but if extra uses are added extra fields may be needed.
  getUnitData = function (context, witness_list, success_callback) {
    var search = {'basetext': CL.dataSettings.base_text, 'context': context, '_fields': 'siglum,witnesses,duplicate_position,transcription,transcription_identifier,public,identifier'};
    //extra check for Django because sometimes we are given identifier and sometimes id
    //TODO: check if this is needed
    if (isNaN(parseInt(witness_list[0]))) {
      search.transcription__identifier = witness_list.join();
    } else {
      search.transcription__id = witness_list.join();
    }
    $.ajax({'url': 'collation/collationdata',
        'method': 'GET',
        'data': search}
    ).done(function (response) {
      if (typeof success_callback !== 'undefined') {
        success_callback(response);
      }
    }).fail(function (response) {
      if (typeof error_callback !== 'undefined') {
        error_callback(response);
      } else {
        console.log('could not retrieve collation data for ' + context);
      }
    });
    return;
  };

  getSiglumMap = function (id_list, result_callback) {
    if (id_list.length > 0) {
      api.getItemsFromDatabase('transcriptions', 'transcription', {'identifier': id_list.join(), '_fields': 'id,identifier,siglum', 'limit': 100000}, 'GET', function(response) {
        var transcription_list;
        transcription_list = response.results;
        var siglum_map = {};
          for (let i = 0; i < transcription_list.length; i += 1) {
            if (id_list.indexOf(transcription_list[i].identifier) !== -1) { //extra test for bug which returns too much data if a single empty string in id list
              //TODO: consider this. Using identifier is better for understanding but you will need to remember to do all lookupd using this and that means they all have to be done in services
      		    siglum_map[transcription_list[i].siglum] = transcription_list[i].identifier;
            }
      	  }
      	  result_callback(siglum_map);
      });
    } else {
      result_callback({});
    }
  };

  //TODO: merge this with context input?
  getWitnessesFromInputForm = function() {
    var witness_list, data, key;
    if (document.getElementById('preselected_witnesses')) {
      witness_list = document.getElementById('preselected_witnesses').value.split(',');
    } else {
      //TODO: test this
      witness_list = [];
      data = cforms.serialiseForm('collation_form');
      if (!$.isEmptyObject(data)) {
        witness_list = [];
        for (key in data) {
          if (data.hasOwnProperty(key)) {
            if (data[key] !== null) {
              witness_list.push(key);
            }
          }
        }
        if (witness_list.indexOf(CL.dataSettings.base_text) === -1) {
          witness_list.push(CL.dataSettings.base_text);
        }
      }
    }
    return witness_list;
  };

  updateRuleset  = function (for_deletion, for_global_exceptions, for_addition, verse, success_callback) {
    var for_ge;
    if (for_deletion.length > 0) {
      //TODO: consider changing decision to rule
      //TODO: if you make a list delete function use that here
      api.deleteItemFromDatabase('collation', 'decision', for_deletion[0].id, function (deleted) {
        console.log(JSON.parse(JSON.stringify(for_deletion)));
        for_deletion.shift(); //remove the first item from the list
        console.log(JSON.parse(JSON.stringify(for_deletion)));
        return updateRuleset(for_deletion, for_global_exceptions, for_addition, verse, success_callback);
      });
    } else if (for_global_exceptions.length > 0) {
      api.getItemFromDatabase('collation', 'decision', for_global_exceptions[0].id, CL.project.id, function (response) {
        if (response.hasOwnProperty('exceptions') && response.exceptions !== null) {
          if (response.exceptions.indexOf(verse) === -1 && verse) {
            response.exceptions.push(verse);
          }
        } else {
          response.exceptions = [verse];
        }
        api.updateItemInDatabase('collation', 'decision', response, function () {
          for_global_exceptions.shift();
          return updateRuleset(for_deletion, for_global_exceptions, for_addition, verse, success_callback);
        });
      });
    } else if (for_addition.length > 0) {
      api.createItemInDatabase('collation', 'decision', fix_classification_key(for_addition[0]), function(response) {
        for_addition.shift();
        return updateRuleset(for_deletion, for_global_exceptions, for_addition, verse, success_callback);
      });
    } else {
      if (success_callback) success_callback();
    }
  };

  // if verse is passed, then verse rule; otherwise global
  //TODO: this is only used in global exception editing. If this remains the case change name
  //This must handle the concurrency control of the database so I am redoing the exception removal here
  //this does not need to be replicated in local services or any service in which rules are not shared by mupltiple users
  // as concurrency control is not an issue
  updateRules = function(rules, verse, success_callback) {
    if (rules.length === 0) {
      if (success_callback) success_callback();
      return;
    }
    api.getItemFromDatabase('collation', 'decision', rules[0].id, CL.project.id, function (response) {
      if (response.hasOwnProperty('exceptions') && response.exceptions !== null) {
        if (response.exceptions.indexOf(verse) !== -1) {
          response.exceptions.splice(response.exceptions.indexOf(verse), 1);
          if (response.exceptions.length === 0) {
            response.exceptions = null;
          }
        }
      }
      api.updateFieldsInDatabase('collation', 'decision', response.id, {'exceptions': response.exceptions}, function() {
        rules.shift();
        return updateRules(rules, verse, success_callback);
      });
    });
  };


  getRulesByIds = function(ids, result_callback) {
    api.getItemsFromDatabase('collation', 'decision', {'project__id': CL.project.id, 'limit': 1000000, 'id': ids.join()}, 'GET', function (response) {
      result_callback(response.results);
    });
  };

  fix_classification_key = function (rule) {
    if (rule.hasOwnProperty('class')) {
      rule.classification = rule.class;
      delete rule.class;
    }
    return rule;
  };


  // TODO: work out why this is returning each rule 7 times
  //get all rules that could be applied to the given verse
  getRules = function (verse, result_callback) {
    getUserInfo(function(current_user) {
      var shared, always, rules;
      if (current_user) {
        if (CL.project.hasOwnProperty('id')) {
          shared = {'limit': 1000000, 'project__id': CL.project.id};
        } else {
          shared = {'limit': 1000000, 'user__id': current_user._id};
        }
      } else {
        //Should never happen as this would mean noone is logged in
        shared = {};
      }
      rules = [];
      //get global rules
      always = JSON.parse(JSON.stringify(shared));
      always.scope = 'always';
      always.exceptions = '!' + verse;
      api.getItemsFromDatabase('collation', 'decision', always, 'GET', function (glbl) {
        rules.push.apply(rules, glbl.results);
        verse_once = JSON.parse(JSON.stringify(shared));
        verse_once.scope = 'verse,once';
        verse_once.context__unit = verse;
        api.getItemsFromDatabase('collation', 'decision', verse_once, 'GET', function (veronce) {
          rules.push.apply(rules, veronce.results);
          ms = JSON.parse(JSON.stringify(shared));
          ms.scope = 'manuscript';
          api.getItemsFromDatabase('collation', 'decision', ms, 'GET', function (manu) {
            rules.push.apply(rules, manu.results);
            for (let i=0; i<rules.length; i+=1) {
              if (rules[i].hasOwnProperty('classification')) {
                rules[i]['class'] = rules[i].classification;
                delete rules[i].classification;
              }
            }
            result_callback(rules);
          });
        });
      });
    });
  };

  getRuleExceptions = function(verse, result_callback) {
	    //could add a get user in here and do the rest in the callback
	    //TODO: if project use project else use user
      api.getItemsFromDatabase('collation', 'decision', {'limit': 1000000,'scope': 'always', 'project__id': CL.project.id, 'exceptions': verse}, 'GET', function (response) {
        result_callback(response.results);

      });
  };

  doCollation = function(verse, options, result_callback) {
    var url;
    if (typeof options === "undefined") {
      options = {};
    }
    url = 'collation/collationserver/';
    if (options.hasOwnProperty('accept')) {
      url += options.accept;
    }
    //force splitting of single reading units for MUYA because it suites their editorial policy better
    options.configs.split_single_reading_units = true;
    $.post(url, { options : JSON.stringify(options) }, function(data) {
      result_callback(data);
    }).fail(function(o) {
      result_callback(null);
    });
  };

  applySettings = function (data, resultCallback) {
    var url;
    url = '/collation/applysettings/';
    $.ajax({
      type: 'POST',
      url: url,
      data: {'data' :JSON.stringify(data)},
      success: function(data){
        resultCallback(data);
      }}).fail(function(o) {
        resultCallback(null);
    });
  };


  getAdjoiningUnit = function(context, isPrevious, result_callback) {
    if (!CL.dataSettings.hasOwnProperty('base_text') || CL.dataSettings.base_text === '') {
      return result_callback(null);
    }
    // get the current verse from the base_text - this assumes identifier string used to identify basetext
    api.getItemsFromDatabase('transcriptions', 'collationunit', {'transcription__identifier': CL.dataSettings.base_text, 'context': context, '_fields': 'siglum,context,index,transcription_identifier'}, 'GET', function (response) {
      var newIndex;
      if (response.results.length !== 1) {
        return result_callback(null);
      }
      index = response.results[0].index;
      if (isPrevious) {
        newIndex = index-1;
      } else {
        newIndex = index+1;
      }
      // get the next/previous verse context from the base_text
      api.getItemsFromDatabase('transcriptions', 'collationunit', {'transcription_identifier': response.results[0].transcription_identifier, 'index': newIndex, '_fields': 'siglum,context,index'}, 'GET', function (response) {
        if (response.results.length !== 1) {
          return result_callback(null);
        }
        return result_callback(response.results[0].context);
      });
    });
  };


  // save a collation
  // result: true if saved and successful, false otherwise
  saveCollation = function(context, collation, confirm_message, overwrite_allowed, no_overwrite_message, result_callback) {
    //add in the MUYA specific stuff we need
    var temp;
    collation.identifier = collation.id;
    delete collation.id;
    temp = context.split('.');
    collation.line_number = parseInt(temp[3]);
    collation.stanza_number = parseInt(temp[2]);
    collation.chapter_number = parseInt(temp[1]);


    //get work from project
    api.getItemFromDatabase('collation', 'project', collation.project, undefined, function(project) {
      collation.work = project.work;
      //see if we already have a saved version with this identifier (and project due to model restrictions)
      api.getItemsFromDatabase('collation', 'collation', {'identifier': collation.identifier, 'project__id': project.id}, 'GET', function (response) {
        if (response.count === 0) {
          //then this is a new collation to save
          api.createItemInDatabase('collation', 'collation', collation, function () {
            //successfully created
            result_callback(true);
            return;
          }, function () {
            result_callback(false);
            return;
          });
        } else if (response.count === 1) {
          //a saved collation already exists
          var confirmed;
          if (overwrite_allowed) {
            if (confirm_message === undefined) {
              confirmed = true;
            } else {
              confirmed = confirm(confirm_message);
            }
            if (confirmed === true) {
              //user decided to overwrite so do that
              collation.id = response.results[0].id;
              api.updateItemInDatabase('collation', 'collation', collation, function() {
                //here if it is approved remove the text selected version if exists
                if (collation.status === 'approved') {
                  criteria = {'status': 'edited',
                              'project__id': collation.project,
                              'context': collation.context
                              };
                  api.getItemsFromDatabase('collation', 'collation', criteria, 'GET', function (edited_collations) {
                    if (edited_collations.results.length === 1) {
                      api.deleteItemFromDatabase('collation', 'collation', edited_collations.results[0].id, function () {
                        result_callback(true);
                        return;
                      });
                    } else {
                      result_callback(true);
                      return;
                    }
                  });
                } else {
                  result_callback(true);
                  return;
                }
              }, function () {
                result_callback(false);
                return;
              });
            } else {
              //user decided not to overwrite
              result_callback(false);
              return;
            }
          } else {
            //no permission to overwrite existing saved version
            alert(no_overwrite_message);
            result_callback(false);
            return;
          }
        } else {
          alert('There are too many saved versions of this collation. Please contact your systems administrator.');
          result_callback(false);
          return;
        }
      });
    });
  };

  getApparatusForContext = function (successCallback)  {
    var url, format, callback;
    format = 'latex';
    url = '/collation/apparatus';
    callback = function(collations) {
        var collationId, innerCallback;
        for (let i=0; i<collations.length; i+=1) {
            if (collations[i].status === 'approved') {
                collationId = collations[i].id;
            }
        }
        innerCallback = function (collation) {
            $.post(url, {
              csrfmiddlewaretoken: api.getCSRFToken(),
              settings: CL.getExporterSettings(),
              format: format,
              data: JSON.stringify([{
                "context": CL.context,
                "structure": collation.structure
                }])
            }).then(function (response) {
                var blob, filename, downloadUrl, hiddenLink;
                if (format === 'latex') {
                    blob = new Blob([response], {'type': 'text/txt'});
                    filename = CL.context + '_' + format + '_apparatus.txt';
                } else {
                    blob = new Blob([response], {'type': 'text/xml'});
                    filename = CL.context + '_' + format + '_apparatus.xml';
                }
                downloadUrl = window.URL.createObjectURL(blob);
                hiddenLink = document.createElement('a');
                hiddenLink.style.display = 'none';
                hiddenLink.href = downloadUrl;
                hiddenLink.download = filename;
                document.body.appendChild(hiddenLink);
                hiddenLink.click();
                window.URL.revokeObjectURL(downloadUrl);
                if (successCallback) {
                    successCallback();
                }
            }).fail(function (response) {
                alert('This unit cannot be exported. First try reapproving the unit. If the problem persists please ' +
                      'recollate the unit from the collation home page.');
            });
        };
        loadSavedCollation(collationId, innerCallback);
    };
    getSavedCollations(CL.context, undefined, callback);

  };


  //TODO: think about adding an optional stage argument here so we can get very specific things back.
  //would make the checks needed for adding and removing a little bit quicker
  getSavedCollations = function(context, user_id, result_callback) {
    var criteria;
    criteria = {};
    criteria.context = context;
    CL.services.getUserInfo(function(current_user) {
      if (current_user) {
        if (CL.project.hasOwnProperty('id')) {
          criteria.project__id = CL.project.id;
        } else {
          criteria.user__id = current_user.id;
        }
        if (user_id) {
          criteria.user__id = user_id;
        }
        criteria._fields = 'id,user,status,data_settings,last_modified_time,created_time';
        api.getItemsFromDatabase('collation', 'collation', criteria, 'GET', function (response) {
          result_callback(response.results);
        });
      }
    });
  };

  getUserInfoByIds = function(ids, success_callback) {
    $.ajax({'url': '/collation/whoarethey',
            'method': 'GET',
            'data': {ids: ids.join()}
    }).done(function (response) {
      if (typeof success_callback !== 'undefined') {
        success_callback(response);
      }
    }).fail(function (response) {
      success_callback(null);
    });
  };

  loadSavedCollation = function(id, result_callback) {
    api.getItemsFromDatabase('collation', 'collation', {'project__id': CL.project.id, 'id': id}, 'GET', function(response) {
      result_callback(response.results[0]);
    }, function() {
      result_callback(null);
    });
  };

  // this populates the links in the footer to the different stages. At the request of the project team it provides
  // links to the versions saved by the managing editor rather than the current user.
  getSavedStageIds = function(context, result_callback) {
    CL.services.getCurrentEditingProject(function (project){
        if (project) {
            var r, s, o, a, results, user_id, criteria, criteria_1, criteria_2, i;
            r = null;
            s = null;
            o = null;
            a = null;
            //first get all of the ones belonging to the managing editor
            criteria = {'user__id': project.managing_editor, 'context': context};
            if (CL.project.hasOwnProperty('id')) {
              criteria.project__id = CL.project.id;
            }
            api.getItemsFromDatabase('collation', 'collation', criteria, 'GET', function (response) {
              results = response.results;
              //now get the approved version for the project
              if (CL.project.hasOwnProperty('id')) {
                criteria = {'context': context, 'project__id': CL.project.id, 'status': 'approved'};
                api.getItemsFromDatabase('collation', 'collation', criteria, 'GET', function (response) {
                  results.push.apply(results, response.results);
                  for (i = 0; i < results.length; i += 1) {
                    if (results[i].status === 'regularised') {
                      r = results[i].id;
                    } else if (results[i].status === 'set') {
                      s = results[i].id;
                    } else if (results[i].status === 'ordered') {
                      o = results[i].id;
                    } else if (results[i].status === 'approved') {
                      a = results[i].id;
                    }
                  }
                  result_callback(r, s, o, a);
                });
              } else {
                for (i = 0; i < results.length; i += 1) {
                  if (results[i].status === 'regularised') {
                    r = results[i].id;
                  } else if (results[i].status === 'set') {
                    s = results[i].id;
                  } else if (results[i].status === 'ordered') {
                    o = results[i].id;
                  } else if (results[i].status === 'approved') {
                    a = results[i].id;
                  }
                }
                result_callback(r, s, o, a);
              }
            });
        }
    });
  };

  addExtraFooterFunctions = function() {
    $('#show_ritual_directions').on('click', function () {
      LOCAL.showRitualDirections();
    });
  };

  extractWordsForHeader = function (data) {
    return LOCAL.extractWordsForHeader(data);
  };

  return {

    contextInput: contextInput,
    supportedRuleScopes: supportedRuleScopes,
    localJavascript: localJavascript,
    witnessSort: witnessSort,
    preStageChecks: preStageChecks,
    ruleConditions: ruleConditions,
    extraFooterButtons: extraFooterButtons,
    overlappedOptions: overlappedOptions,
    displaySettings: displaySettings,
    initialiseEditor: initialiseEditor,
    getCurrentEditingProject: getCurrentEditingProject,
    getUnitData: getUnitData,
    getSiglumMap: getSiglumMap,
    updateRuleset: updateRuleset,
    getRules: getRules,
    doCollation: doCollation,
    getWitnessesFromInputForm: getWitnessesFromInputForm,
    getAdjoiningUnit: getAdjoiningUnit,
    getUserInfo: getUserInfo,
    getRuleExceptions: getRuleExceptions,
    getRulesByIds: getRulesByIds,
    updateRules: updateRules,
    saveCollation: saveCollation,
    getSavedCollations: getSavedCollations,
    getUserInfoByIds: getUserInfoByIds,
    loadSavedCollation: loadSavedCollation,
    getSavedStageIds: getSavedStageIds,
    getApparatusForContext: getApparatusForContext,
    showLoginStatus: showLoginStatus,
    combineAllLacsInOR: combineAllLacsInOR,
    combineAllOmsInOR: combineAllOmsInOR,
    combineAllLacsInApproved: combineAllLacsInApproved,
    combineAllOmsInApproved: combineAllOmsInApproved,
    lac_unit_label: lac_unit_label,
    om_unit_label: om_unit_label,
    applySettings: applySettings,
    ruleClasses: ruleClasses,
    undoStackLength: undoStackLength,
    allowWitnessChangesInSavedCollations: allowWitnessChangesInSavedCollations,
    addExtraFooterFunctions: addExtraFooterFunctions,
    extractWordsForHeader: extractWordsForHeader,
    exporterSettings: exporterSettings,
      localCollationFunction, localCollationFunction,

  };

} () );
