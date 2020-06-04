var code_highlight_palette = ["#cae2dc", "#eee3cd", "#cad7f2", "#ded4e7", "#e3e3e3", "d6eff0"];

var decodeHTML = function (html) {
  var txt = document.createElement('textarea');
  txt.innerHTML = html;
  return txt.value;
}

var html_space_replace = function(){
  var leadingSpaces = arguments[0].length;
  var str = '';
  while(leadingSpaces > 0) {
    str += '&nbsp;';
    leadingSpaces--;
  }
  return str;
}

var subatom_click = function(dict){app.$emit("subatom-selected", dict)}

Vue.component("machine-function-property", {
  props: ['tree'],
  template : `
    <div class="panel panel-success">
      <div class="panel-heading">
        <h3 class="panel-title" id="function-title" @click="showFunctions=!showFunctions">Machine / Function / Property</h3>
      </div>
      <div class="panel-body">
        <transition name="slide-fade">
        <div v-show="showFunctions" class="list-group" id="function-list">
          <div id="function-list-data"></div>
          <div class="tab">
            <button v-for="(value,key) in tree" :class="(key===showTab)? 'tablinks active':'tablinks' " @click="selectTab(key)">{{key}}</button>
          </div>
          <subtree v-for="(value,key) in tree" v-show="(key === showTab)" :key="key" :id="key" :content="value"> </subtree>
        </div>
        </transition>
      </div>
    </div>`,
  data() {
    return {showTab: "", showFunctions: true}
  },
  methods : {
    selectTab: function(selectedTab){
      // selectedTab contains the ID of the tabcontent element which needs to be displayed
      this.showTab = selectedTab;

    }
  },
  mounted() {
    var machine_keys=[];
    for (key in this.tree){
      machine_keys.push(key)
    }
    this.selectTab(machine_keys[0]);
    var remember_this = this;
    this.$root.$on('function-select', function(dict){
      remember_this.showFunctions = false;
    })
  }
})

Vue.component("subtree",{
  props: ['id', 'content'],
  template:  `
    <div class="tabcontent" :id=this.tabid>
      <subtreelevel :htmlcontent="content" :path="id"> </subtreelevel>
    </div>`,
  data() {
    return { tabid: "tab-" + this.id }
  }
})

Vue.component("subtreelevel", {
  /*recursive component, properties store the following information:
  htmlcontent - function tree based on which the html of the element is built, updated for each level
  path - the path through the function tree to the current element
  panelid, stylepadding - strings which are used to define the header on each level
  keyname - title in the header, taken as a dictionary key on the current tree level

  after adding the header for the current level, iterate through the lower level to repeat the process
  if the subtreelist is empty, this is an indicator that we reached the last level
  - this means it is time to display the specification - the recursion stops here*/
  props: ['htmlcontent', 'path', 'panelid', 'stylepadding', 'keyname'],
  template: `
    <div class="panel panel-default" style="inherit">
      <div v-if="keyname" class="panel-heading">
        <h3 class="panel-title" :id="this.panelid" :style="this.stylepadding"> {{this.keyname}} </h3>
      </div>
      <div class="panel-body">
        <div class="list-group" :id="path">
          <subtreelevel v-for="(level,index) in this.subtreeslist" :key="index" :htmlcontent="level.nextcontent"
          :path="level.nextpath" :panelid="level.panelid" :stylepadding="level.stylepadding"
          :keyname="level.keyname"></subtreelevel>
          <div v-if="!this.subtreelist">
            <button v-for="(b, index) in this.buttons" type="button" class="list-group-item"
              :function-id="b.functionid" :style="b.padding" @click="selectFunction(b.functionid, b.str)">
              <specification :spec=b.str :change="0"></specification>
            </button>
          </div>
        </div>
      </div>
    </div>
    `,
  data() {
    // take subtree and path from properties parsed to this component
    var subtree = JSON.parse(JSON.stringify(this.htmlcontent));
    var path = this.path;
    var padding = String(path.split("-").length * 20) + "px";

    // check if the last level is reached - if it is, return an empty subtrees list to indicate this
    // also return the HTML needed to build the element with the specification
    if(Array.isArray(subtree)) {
      var buttons = [];
      for(var i=0; i<subtree.length; i++) {
        var str = subtree[i][2];
        //str = decodeHTML(str);
        buttons.push({functionid: subtree[i][0], padding : "padding-left:" + padding, str : str});
      }
      return {buttons: buttons, subtreeslist:[]}

    // if this is not the last level, iterate through the keys in the subtree and return the list
    // based on which new subtree components will be defined
    } else {
      var keys = [];
      for (var key in subtree) {
        keys.push(key);
      }
      console.log("path="+path+"; keys="+ keys);

      var dicts_list = [];
      for(var i=0; i<keys.length; i++) {
        var key = keys[i];
        // create list inside the current list in the dom
        var new_path = (path != "") ? (path + "-" + key) : key;
        var panel_id = "external-" + new_path;
        var style_padding = "padding-left: " + padding;
        console.log(JSON.stringify(subtree[key]))
        dicts_list.push({keyname: key,
          nextcontent : subtree[key], nextpath : new_path,
          stylepadding : style_padding, panelid : panel_id});
      }
      return {subtreeslist : dicts_list}
    }
  },
  methods : {
    selectFunction: function(id, code){
      console.log(id)
      this.$root.$emit('function-select', {selected_function_id: id, specification_code: code})
    }
  }
})

Vue.component("function-calls", {
  template : `
    <div class="panel panel-success">
      <div class="panel-heading">
        <h3 class="panel-title" id="function-call-title">Function Call</h3>
      </div>
      <div class="panel-body">
        <div class="list-group" id="function-call-list">
          <div v-if="message" class="please-select"><p>{{message}}</p></div>
          <button v-for="(b, index) in this.buttons" :key="index" class="list-group-item">
            <input type='checkbox' :function-call-id="b.callid" :value="b.callid" v-model="checkedCalls"/>
            <b>Start:</b> {{b.callstart}}, <b>lasting: </b> {{b.callduration}} seconds
          </button>
        </div>
      </div>
    </div>`,
  data() {
    return { message : "Select a function first.", buttons : [], checkedCalls: [] }
  },
  methods : {
    showCalls: function(dict){
      /**/
    }
  },
  mounted(){
    var obj = this;
    this.$root.$on('function-select', function(dict){
      console.log(dict);

      obj.message = "Loading function calls.  This can take some time if there are many.";
      obj.buttons = [];
      obj.checkedCalls = [];
      console.log(obj.message)

      axios.get('/list_function_calls/'+dict["selected_function_id"]).then(function(response){
        var data = response.data["data"];
        obj.message = "";
        var buttons_list = [];
        for(var i=0; i<data.length; i++) {
          var button = {callid : data[i][0], callstart: data[i][2], callduration: data[i][6]}
          buttons_list.push(button)
        }
        obj.buttons = buttons_list;
        console.log("data updated");
        obj.$root.$emit('calls-loaded', dict);

      })


    })
  },
  watch: {
    checkedCalls: function(value){
      console.log(value)
      var function_call_ids = [];
      var that = this;
      for (var i=0; i<value.length; i++){
        function_call_ids.push(""+value[i]);
      }
      if (function_call_ids.length){
        axios.post("/get_function_calls_data/", {"ids" : function_call_ids}).then(function(response) {
          tree = response.data;
          console.log(JSON.stringify(tree))
          that.$root.$emit('calls-selected',tree);
        });
      }
    }
  }
})

Vue.component("code-view", {
  template : `
    <div class="panel panel-success">
      <div class="panel-heading">
        <h3 class="panel-title">Code View</h3>
      </div>
      <div class="panel-body" id="verdict-list">
        <div v-if="message" class="please-select">{{message}}</div>
        <div v-if="specification_code" id='specification_listing'>
          <specification :spec="this.specification_code" :change="1" />
        </div>
        <div v-if="code_lines" class='code_listing'>
          <div v-for="(line,index) in code_lines" :key="index" :class="line.class"
          :id="line.id" :style="line.background" :save-background-color="line.color"
          v-show="line.show">
            <b> {{line.line_number}} </b> <span v-html="line.content"> </span>
            <span class="span-binding" :id="line.spanid"><button v-for="b in line.buttons"
            class="binding-button" :binding-button="b.binding" :style="b.font"
            @click="selectBinding(b.binding, b.subtree, b.lines)">
            {{b.binding}}</button></span>
            <p v-show="line.showempty" class="empty-line" :id="line.emptyid"> ... <br> </p>
            <dropdown v-if="line.addmenu" :tree="this.tree" :dict="line.dict"
              :binding="this.binding" :line=line.line_number> </dropdown>
          </div>
        </div>
      </div>
    </div>`
  ,
  data(){
    return {message: "Select a function and then one or more calls, first.",
            specification_code: "", code_lines: [], start_line: 0, tree: {}, binding: undefined}
  },
  methods:{
    selectBinding : function(binding, tree, lines){
      // binding stores the index of the binding, tree is the branch tree[binding]
      // lines is a list of line numbers that need to be highlighted

      var whole_code = this.code_lines;
      var start_line = this.start_line;

      // reset the background colors of previously highlighted lines
      for (var i=0; i<whole_code.length; i++){
        var line = whole_code[i];
        line.addmenu = false;
        if (line.color){
          line.background = "background-color: #ebf2ee";
        }
        for (var j=0; j<line.buttons.length; j++){
          if (line.buttons[j].binding == binding){
            line.buttons[j].font = "font-weight: bold";
          }
          else{
            line.buttons[j].font = "font-weight: normal";
          }
        }
      }

      for (var i=0; i<lines.length; i++){
        var line = whole_code[lines[i]-start_line];
        line.background = "background-color: " + line.color;
      }
      this.binding = binding;
      this.tree = tree;
      this.$root.$emit("binding-selected", tree);
    }
  },
  mounted(){
    var obj2 = this;
    this.$root.$on('calls-loaded', function(dict){
      obj2.message = "";
      obj2.specification_code = dict["specification_code"];
      axios.get('/get_source_code/'+dict["selected_function_id"]).then(function(response){
        var code_data = response.data;
        var code_lines = code_data["code"];
        var current_line = code_data["start_line"];
        obj2.start_line = current_line;

        // we also want to display binding reference at the end of each line
        // first, go through bindings and collect all line numbers they refer to
        var bindings_list = code_data["bindings"];
        var line_numbers = [];
        for (var i=0; i<bindings_list.length; i++){
          binding = bindings_list[i];
          line_numbers = line_numbers.concat(binding["binding_statement_lines"]);
        }

        // add each line as a div element, if it is in the list of binding statement lines,
        // also add a span element to the content of the line - later, we will add binding labels to it
        var lines_list = [];
        for(var i=0; i < code_lines.length; i++) {
          var line_text = code_lines[i].replace(/\t/g, "&nbsp;&nbsp;&nbsp;").replace(/^[ \t]+/mg, html_space_replace);
          var line_div = {line_number: current_line, id: "line-number-" + current_line,
                          background: "background-color: transparent", color: "", show: true,
                          added_empty_line: false, spanid: "span-bindings-line-" + current_line,
                          content: line_text, buttons: [], emptyid: "empty-line-" + current_line,
                          showempty: false, addmenu: false, class: "code_listing_line", dict: {}}


          lines_list.push(line_div);
          current_line++;
        }

        obj2.code_lines = lines_list;


        // we want to highlight the quantification in the specification code
        // with the same color as the line of code it refers to
        var quantification_ids = obj2.specification_code["vars"].split(", ");

        // for each binding line go through the specification to find the quantification
        // that refers to that line and highlight it the same color as the line in the code
        for (var i=0; i<bindings_list.length; i++){
          var binding = bindings_list[i];
          var line_numbers = binding["binding_statement_lines"];

          for (var j=0; j<line_numbers.length; j++){
            var no = line_numbers[j]
            var color = code_highlight_palette[j];
            lines_list[no-code_data["start_line"]].background = "background-color: "+color;
            lines_list[no-code_data["start_line"]].color = color;
            //$("#span-bindings-line-"+no).append(" "+binding["id"]);
          } //end j-loop
        } //end i-loop
      })
    })
    this.$root.$on('calls-selected', function(tree){
      console.log(tree)
      obj2.tree = tree;

      var show_lines = []; //stores all lines that are of interest plus a few around them - we will hide the rest
      var start_line = obj2.start_line;
      var whole_code = obj2.code_lines;

      //clean up the binding buttons and dropdown menusfrom previous selection
      for (var i=0; i<whole_code.length; i++){
        whole_code[i].buttons = [];
        whole_code[i].addmenu = false;
      }

      // iterate through the bindings to highlight the lines and separate those paired with
      // a quantifier from those that are of interest because a subatom generates observations there
      for (binding in tree){
        var line_numbers = []; //stores all points of interest
        var lines_points = []; //stores only those stored by bindings
        for (atom in tree[binding]){
          for (subatom in tree[binding][atom]){
            list = tree[binding][atom][subatom];
            for (var i=0; i<list.length; i++){
              if (line_numbers.indexOf(list[i]["code_line"])==-1){
                line_numbers.push(list[i]["code_line"]);
              }
              if (atom=="-1" && lines_points.indexOf(list[i]["code_line"])==-1){
                lines_points.push(list[i]["code_line"]);
              }

            }
          }
        }
        show_lines = show_lines.concat(line_numbers);
        console.log(line_numbers)
        console.log(lines_points)
        for (var i=0; i<line_numbers.length; i++){
          var no = line_numbers[i] - obj2.start_line;
          whole_code[no].background = "background-color: #ebf2ee"
          color = whole_code[no].color;
          if (!(color)){
            whole_code[no].color = "#def1fc";
          }
        }
        for (var i=0; i<lines_points.length; i++){
          var no = lines_points[i];
          whole_code[no-start_line].buttons.push({binding: binding, subtree: tree[binding],
            lines: line_numbers, font: "font-weight: normal"});
          }
        }

      show_lines = show_lines.sort();

      //in addition to the lines stored in leaves, we want to display the first line
      // and in this case, three lines around each instrumentation point
      var more_lines = [obj2.start_line];
      for (var i=0; i<show_lines.length; i++){
        var current_line_number = show_lines[i];
        for (var j=1; j<3; j++){
          more_lines.push(current_line_number+j);
          more_lines.push(current_line_number-j)
        }
      }
      show_lines = show_lines.concat(more_lines);

      for (var i=0; i<whole_code.length; i++){
        var line_id = whole_code[i].id.split("-");
        var id_line_number = line_id[line_id.length-1];
        if (show_lines.indexOf(parseInt(id_line_number))==-1){
          whole_code[i].show = false;
        }
        else{
          whole_code[i].show = true;
        }
      }

      // insert a spacing where there is a jump in line numbers
      show_lines = show_lines.sort(function(a, b){return a - b});

      for (var i=0; i<show_lines.length; i++){
        if (show_lines[i] < (show_lines[i+1] - 1)){
          whole_code[show_lines[i]-obj2.start_line].showempty = true;
        }
        else{
          whole_code[show_lines[i]-obj2.start_line].showempty = false;
        }
      }
    })
    this.$root.$on("subatom-selected", function(dict){
      var atom_index = dict["atom"];
      var sub_index = dict["subatom"];
      var inst_points_list = obj2.tree[atom_index][sub_index];
      var whole_code = obj2.code_lines;

    	var lines_list = [];
    	for (var i=0; i<inst_points_list.length; i++){
    		var no = inst_points_list[i]["code_line"];
    		//$("#line-number-"+no).attr('save-background-color',color);
    		lines_list.push(no);
    	}

      for (var i=0; i<whole_code.length; i++){
        if (whole_code[i].color) {
          whole_code[i].background = "background-color: #ebf2ee";
          whole_code[i].addmenu = false;
        }
      }

      for (var i=0; i<lines_list.length; i++){
        var line = whole_code[lines_list[i]-obj2.start_line]
        line.background = "background-color: " + line.color;
        line.addmenu = true;
        line.class = "code_listing_line code_listing_line-clickable";
        line.dict = dict;
      }
    })
  }
})

Vue.component("specification", {
  props: ['spec', 'change'],
  template: `
    <div>
      <p v-for="(v, index) in this.bindvars" class="list-group-item-text code" :id="v.id" v-html="v.forall"
          :style="v.background"> </p>
      <p class="list-group-item-text code">Check( </p>
      <p class="list-group-item-text code" v-html="this.vars"></p>
      <p class="list-group-item-text code" v-html="this.str"></p>
      <p class="list-group-item-text code">&nbsp;&nbsp;) </p>
      <p class="list-group-item-text code">)</p>
    </div>`,
  data(){
    var spec_dict = this.spec;
    var list = spec_dict["foralls"];
    var bindvars = [];
    for (i=0; i<list.length; i++){
      var bg;
      if (this.change==1){
        bg = "background-color: " +
          code_highlight_palette[spec_dict["vars"].split(", ").indexOf(list[i]["var_id"])] + ";";
      }
      else{
        bg = "background-color: transparent;";
      }
      bindvars.push({id: list[i]["var_id"],
                     forall: "Forall("+list[i]["var_forall"]+").\ ",
                     background: bg})
    }
    return {
      vars : "&nbsp;&nbsp;lambda  : ( " + spec_dict["vars"],
      str : "&nbsp;&nbsp;&nbsp;&nbsp; " + spec_dict["atom_str"],
      bindvars: bindvars
    }
  },
  watch: {
    spec(newValue) {
      var spec_dict = newValue;
      var list = spec_dict["foralls"];
      var bindvars = [];
      for (i=0; i<list.length; i++){
        var bg;
        if (this.change==1){ bg = "background-color: " +
            code_highlight_palette[spec_dict["vars"].split(", ").indexOf(list[i]["var_id"])] + ";";}
        else { bg = "background-color: transparent;";}
        bindvars.push({id: list[i]["var_id"],
                       forall: "Forall("+list[i]["var_forall"]+").\ ",
                       background: bg})
      }
      this.vars = "&nbsp;&nbsp;lambda  : ( " + spec_dict["vars"];
      this.str = "&nbsp;&nbsp;&nbsp;&nbsp; " + spec_dict["atom_str"];
      this.bindvars = bindvars;
    }
  },
  mounted(){
    var that = this;
    this.$root.$on('calls-selected', function(tree){
      // clean up subatom links from previous binding selection
      remove_subatoms = $(".subatom-clickable");
      if (typeof(remove_subatoms) != 'string'){
      for (var i=0; i<remove_subatoms.length; i++){
        $(remove_subatoms[i]).attr("onclick", "");
        $(remove_subatoms[i]).attr('class', "subatom");
      }}
      $($(".subatom-clickable-active")[0]).attr("onclick","");
      $($(".subatom-clickable-active")[0]).attr("class", "subatom");
    })

    this.$root.$on('binding-selected', function(tree){
      // clean up subatom links from previous binding selection
      remove_subatoms = $(".subatom-clickable");
      if (typeof(remove_subatoms) != 'string'){
      for (var i=0; i<remove_subatoms.length; i++){
        $(remove_subatoms[i]).attr("onclick", "");
        $(remove_subatoms[i]).attr('class', "subatom");
      }}
      $($(".subatom-clickable-active")[0]).attr("onclick","");
      $($(".subatom-clickable-active")[0]).attr("class", "subatom");

      for (atom in tree){
        var subtree = tree[atom];
        var subs = $($("#specification_listing").find('span.atom[atom-index="' + atom + '"]')[0]).children();
        for (var i=0; i<subs.length; i++){
          $(subs[i]).attr('class', "subatom-clickable");
          $(subs[i]).attr('subtree', JSON.stringify(subtree));
          var dict = {atom: atom, subatom: $(subs[i]).attr("subatom-index")};
          $(subs[i]).attr('onclick', 'subatom_click('+JSON.stringify(dict)+')');
        }
      }
    })

    this.$root.$on("subatom-selected", function(dict){
      $($(".subatom-clickable-active")[0]).attr("class", "subatom-clickable");
      var subatom = $($("#specification_listing").find('span.atom[atom-index="' + dict["atom"] + '"]')[0]).find('span[subatom-index="'+dict["subatom"]+'"]')[0];
      $(subatom).attr("class", "subatom-clickable-active");
    })
  }
})

Vue.component("dropdown", {
  props: ["tree", "dict", "binding", "line"],
  template: `
    <div class="dropdown-content">
      <p v-for="option in this.options" class="dropdown-menu-option" @click="selectOption(option.data)">
        {{option.text}} </p>
    </div>
  `,
  data(){
    var options = [];
    var atom_index = this.dict["atom"];
    var sub_index = this.dict["subatom"];
    var inst points = this.tree[this.binding][atom_index][sub_index];
    var inst_point_id = inst_points[0]["id"];
    console.log(inst_point_id)
    var that = this;

    var inst_points_list = [];
    for (var i=0; i<inst_points.length; i++){
      if inst_points[i]["code_line"] == this.line{
        inst_points_list.push(inst_points[i])
      }
    }
    //for a simple atom we now need all observations made at these points,
    //filtered by: calls, binding, atom, subatom
    //then we can calculate verdict severity for each of the observations

    axios.get('/get_atom_type/'+atom_index+"/"+inst_point_id+"/").then(function(response){
      var atom_type = response.data;
      console.log(atom_type);
      if (atom_type == "simple"){
  			option = {text: 'Plot observed values from this point',
                  data: {}};
        options.push(option);
        option = {text: 'Highlight the paths by average verdict severity',
                  data: {}}
        options.push(option);
  		}
  		else if (atom_type == "timeBetween") {
  			option = {text: 'Fix this point and select the other one', data:{}};
        options.push(option);
  		}
  		else if (atom_type == "mixed") {
  			option = {text: 'Fix this point and select the other one', data:{}};
        options.push(option);
  		}
    })
    return{options: options}
  },
  methods: {
    selectOption: function(data){
      console.log("WORKS")
    }
  }
})

var app = new Vue({
    el : "#app"
});
