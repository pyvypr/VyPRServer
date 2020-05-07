var decodeHTML = function (html) {
	var txt = document.createElement('textarea');
	txt.innerHTML = html;
	return txt.value;
}

Vue.component("machine-function-property", {
  props: ['tree'],
  template : `
    <div class="panel panel-success">
      <div class="panel-heading">
        <h3 class="panel-title" id="function-title">Machine / Function / Property</h3>
      </div>
      <div class="panel-body">
        <div class="list-group" id="function-list">
          <div id="function-list-data"></div>
          <div class="tab">
            <button v-for="(value,key) in tree" class="tablinks" @click="selectTab(key)">{{key}}</button>
          </div>
          <subtree v-for="(value,key) in tree" :key="key" :id="key" :content="value"> </subtree>
        </div>
      </div>
    </div>`,
	methods : {
		selectTab: function(selectedTab){
			// selectedTab contains the ID of the tabcontent element which needs to be displayed
			console.log(selectedTab)
			var i, tabcontent, tablinks;
			tabcontent = $(".tabcontent");
			for (i = 0; i < tabcontent.length; i++) {
				tabcontent[i].setAttribute('style', 'display: none');
			}
			tablinks = $(".tablinks")
			for (i=0; i<tablinks.length; i++) {
				tablinks[i].className = "tablinks";
			}
			if (selectedTab != "") {
				$("#"+selectedTab).attr('style', 'display = "block"');
				tablinks = $(".tablinks");
				for (i=0; i<tablinks.length; i++){
					if (tablinks[i].innerHTML == selectedTab){
						tablinks[i].className += " active"
					}
				}
			}
		}
	},
	mounted() {
		var machine_keys=[];
		for (key in this.tree){
			machine_keys.push(key)
		}
		this.selectTab(machine_keys[0]);
	}
}
)

Vue.component("subtree",{
  props: ['id', 'content'],
  template:  `
    <div class="tabcontent" :id="id">
      <subtreelevel :htmlcontent="content" :path="id"> </subtreelevel>
    </div>`
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
							:function-id="b.functionid" :style="b.padding" v-html="b.str"
							@click="selectFunction(b.functionid, b.str)"></button>
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
  			str = decodeHTML(str);
  			buttons.push({ functionid: subtree[i][0], padding : "padding-left:" + padding, str : str});
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
		selectFunction: function(id, specification_code){
			console.log(id)
			$("#function-list").slideUp();
			$("#function-call-list").html("<p>Loading function calls.  This can take some time if there are many.</p>");
			$("#function-call-list").slideDown();
			axios.get('/list_function_calls/'+id).then(function(response){
				var data = response.data["data"];

				$("#function-call-list").html("");
				for(var i=0; i<data.length; i++) {
					var button = document.createElement("button");
					button.className = "list-group-item";
					button.innerHTML = "<input type='checkbox' function-call-id='" + data[i][0]  + "'/><b>Start:</b> " +
					    data[i][2] + ", <b>lasting:</b> " + data[i][6] + " seconds";
					$(button).attr("function-call-id", data[i][0]);
					$("#function-call-list").append(button);
				}

			})
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
          <div class="please-select">Select an http request first.</div>
        </div>
      </div>
    </div>`
  }
)

Vue.component("code-view", {
  template : `
    <div class="panel panel-success">
      <div class="panel-heading">
        <h3 class="panel-title">Code View</h3>
      </div>
      <div class="panel-body" id="verdict-list">
        <div class="please-select">Select a function and then one or more calls, first.</div>
      </div>
    </div>`
  }
)

var app = new Vue({
    el : "#app"
});
