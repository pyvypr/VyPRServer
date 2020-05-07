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
            <button v-for="(value,key) in tree" class="tablinks">{{key}}</button>
          </div>
          <subtree v-for="(value,key) in tree" :key="key" :id="key" :content="value"> </subtree>
        </div>
      </div>
    </div>`
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
  props: ['htmlcontent', 'path', 'panelid', 'stylepadding', 'keyname', 'islast'],
  data() {
    var subtree = JSON.parse(JSON.stringify(this.htmlcontent));
    var path = this.path;
    var padding = String(path.length * 2) + "px";
    if(Array.isArray(subtree)) {
  		var html_string = ""
  		for(var i=0; i<subtree.length; i++) {
  			var str = subtree[i][2];
  			str = decodeHTML(str);

  			html_string += ('<button type="button" class="list-group-item" function-id="' + subtree[i][0] +
  				'" style="padding-left:' + padding + '">' + str + '</button>');
  		}
  		this.subHTML = html_string;
      return {subtreeslist : []}
  	} else {
      var dicts_list = [];
  		var keys = [];
  		for (var key in subtree) {
  			keys.push(key);
  		}
  		console.log("path="+path+"; keys="+ keys);

  		for(var i=0; i<keys.length; i++) {
  			var key = keys[i];
  			// create list inside the current list in the dom
  			var new_path = (path != "") ? (path + "-" + key) : key;
				var panel_id = "external-" + new_path;
				var style_padding = "padding-left: " + padding;
        console.log(JSON.stringify(subtree[key]))
        dicts_list.push({keyname: key, nextcontent : subtree[key], nextpath : new_path, stylepadding : style_padding, panelid : panel_id});
  		}
      return {subtreeslist : dicts_list}
  	}
  },
	template: `
		<div v-if="islast" v-html="subHTML">
		</div>
		<div v-else class="panel panel-default" style="inherit">
			<div class="panel-heading">
				<h3 class="panel-title" :id="this.panelid" :style="this.stylepadding"> {{this.keyname}} </h3>
			</div>
			<div class="panel-body">
				<div class="list-group" :id="path">
					<subtreelevel v-for="(level,index) in subtreeslist" :key="index" :htmlcontent="level.nextcontent" :path="level.nextpath" :panelid="level.panelid" :stylepadding="level.stylepadding" :keyname="level.keyname" :islast="false"></subtreelevel>
				</div>
			</div>
		</div>`
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
