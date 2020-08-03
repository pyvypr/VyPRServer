var Store = {
    status : {
        loading : false,
    },
    plot : {
        constraint_html : "",
        type : null,
        show_violations : true,
        show_successes : true,
        current_hash : null,
        plot_description : null
    },
    path_index : 0,
    selected_function_id : null,
    code_lines : [],
    agreeing_lines : [],
    parameter_lines : [],
    data_per_path : null
};

var html_space_replace = function(){
  var leadingSpaces = arguments[0].length;
  var str = '';
  while(leadingSpaces > 0) {
    str += '&nbsp;';
    leadingSpaces--;
  }
  return str;
}

var generate_plot = function(quantity, root_obj) {
    var that = root_obj;

    // send a request to the server to get the plot data
    axios.get('/get_plot_data_from_hash/' + Store.plot.current_hash).then(function(response){
      // prepare data for plotting
      var data = response.data.data.parameter_values;
      var type = response.data.description.type;
      Store.selected_function_id = response.data.description.function_id;
      Store.plot.type = type;
      that.store.plot.type = type;

      Store.agreeing_lines = response.data.data.main_lines;
      Store.parameter_lines = response.data.data.parameters;
      Store.parameter_values = response.data.data.parameter_values;

      var data_per_path = [];
      for(var path_index=0; path_index<Store.parameter_values.length; path_index++) {

          var myData = [{key: "path index: " + path_index, values: []}];

          if(quantity == "severity") {
            for (var i=0; i<data[path_index]["x"].length; i++) {
              var value = data[path_index]["severities"][i]
              // check whether we should plot this based on the filters
              if(value >= 0) {
                if(!Store.plot.show_successes) continue;
              } else {
                if(!Store.plot.show_violations) continue;
              }
              // negative verdict severity represents violation - colour these bars red
              var color = "#cc0000";
              // other columns in the plot are green since they show non-violating observations
              if (value >= 0) {color = "#00802b"}
              myData[0].values.push({label: new Date(Date.parse(data[path_index]["x"][i])),
                                    value: value,
                                    color: color});
            }

          } else {

            if (type =="mixed-path-observation"){
              myData = [{key: 'subatom 0', values: []}, {key: 'subatom 1', values: []}];
              for (var i=0; i<data[path_index]["x"].length; i++){
                var value1 = data[path_index]["observations_lhs"][i];
                var value2 = data[path_index]["observations_rhs"][i]

                myData[0].values.push({label: new Date(Date.parse(data[path_index]["x"][i])),
                                       value: value1});
                myData[1].values.push({label: new Date(Date.parse(data[path_index]["x"][i])),
                                       value: value2});
              }
            } else {

              for (var i=0; i<data[path_index]["x"].length; i++) {
                myData[0].values.push({label: new Date(Date.parse(data[path_index]["x"][i])),
                                       value: data[path_index]["observations"][i]});
              }
            }

          }

          data_per_path.push(myData);

      }

      Store.data_per_path = data_per_path;

      that.$root.$emit("plot-data-ready", data_per_path);

    });
};

Vue.component("plot", {
  template : `
  <div class="plot">
    <svg :id="svgID" v-bind:class="{hidden : !isSelected}" width="590px" height="360px"></svg>
  </div>
  `,
  props : ["index"],
  data : function() {
    return {
      store : Store
    }
  },
  computed : {
    svgID : function() {
      return "plot-svg-" + this.index;
    },
    isSelected : function() {
      return this.store.path_index == this.index;
    },
    is_mixed_observation_plot : function() {
      return this.store.plot.type == "mixed-observation";
    }
  },
  mounted : function() {
      var that = this;
      // set up the graph
      nv.addGraph(function() {

        //$("#plot-svg-" + that.index).width($("#plot-column").outerWidth()-50);
        //$("#plot-svg-" + that.index).height($("#plot-column").outerHeight()-10);

        var chart = nv.models.multiBarChart()
          .x(function(d) { return d.label })
          .y(function(d) { return d.value })
          .reduceXTicks(true)    //alternatively, use staggering or rotated labels to prevent overlapping
          .showControls(false)
          .showLegend(that.is_mixed_observation_plot);

        // omitting date from time format - mostly the difference is in seconds
        var y_label = that.$root.is_severity_plot ? 'Verdict severity' : 'Observation';
        chart.xAxis
          .axisLabel('Time of observation')
          .tickFormat(function(d) { return d3.time.format('%H:%M:%S')(new Date(d)); });
        chart.yAxis
          .axisLabel(y_label)
          .tickFormat(d3.format('.02f'))
          .showMaxMin(true);

        console.log("building plot for");
        console.log(that.index);
        console.log(Store.data_per_path[that.index]);

        d3.select("#plot-svg-" + that.index)
          .datum(that.store.data_per_path[that.index])
          .call(chart);

        nv.utils.windowResize(chart.update);

        // set initial size
        chart.update();

        return chart;
      });
  }
});

Vue.component("page", {
  template: `<div class="container-fluid plot">
      <div class="col-md-6" id="plot-column">

          <div class="panel panel-success">
            <div class="panel-heading">
              <h3 class="panel-title">Plot</h3>
            </div>
            <div class="panel-body">
              <div id="plot-wrapper" class="plot">
                  <!--<div id="plot-description" v-html="this.description"></div>-->
                  <div id="plot-filters" v-if="is_severity_plot">Filters:
                    <a href="#" id="violations" class="filter" v-bind:class="{active : violationFilterActive}"
                      @click="toggleViolationFilter($event)">Violations</a>
                    <a href="#" id="successes" class="filter" v-bind:class="{active : successFilterActive}"
                      @click="toggleSuccessFilter($event)">Successes</a>
                  </div>
                  <plot v-for="(data, index) in store.data_per_path" :index="index"></plot>
              </div>
            </div>
          </div>

          <div class="panel panel-success">
            <div class="panel-heading">
              <h3 class="panel-title">Options</h3>
            </div>
            <div class="panel-body">
              <ul class="nav nav-pills nav-stacked">
                <li role="presentation"><a href="#" @click="downloadPDF($event)">Download PDF</a></li>
              </ul>
            </div>
          </div>

      </div>

      <div class="col-md-6">
        <div class="panel panel-success">
            <div class="panel-heading">
              <h3 class="panel-title">Paths Taken</h3>
            </div>
            <div class="panel-body code-listing">
              <div v-for="(line,index) in store.code_lines" :class="line.class">
                <span class="line-number"> {{line.line_number}} </span>
                <span class="language-python" v-html="line.content"> </span>
                <button class="btn btn-default parameter" v-bind:class="getClass(index)" v-if="line.is_parameter"
                v-for="(param, index) in store.parameter_values" @click="selectParameter(index)">
                  starting at {{param.lines[0]}}
                </button>
              </div>
            </div>
        </div>
      </div>

      </div>
  </div>
  `,
  props : ["hash", "quantity"],
  data() {
    return {
      store : Store
    }
  },
  computed : {
    violationFilterActive : function() {
      return this.store.plot.show_violations;
    },
    successFilterActive : function() {
      return this.store.plot.show_successes;
    },
    is_severity_plot : function() {
      return this.store.plot.type == "severity" || this.store.plot.type == "between-severity";
    }
  },
  mounted(){
    // store the hash
    this.store.plot.current_hash = this.hash;
    // generate the plot based on the hash
    generate_plot(this.quantity, this);
    this.store.plot.type = Store.plot.type;
    var that = this;
    this.$root.$on("plot-data-ready", function() {

      axios.get('/get_source_code/' + Store.selected_function_id).then(function(response){
      var code_data = response.data;
      var code_lines = code_data["code"];
      var current_line = code_data["start_line"];
      that.start_line = current_line;

      // add each line as a div element, if it is in the list of binding statement lines,
      // also add a span element to the content of the line - later, we will add binding labels to it
      var lines_list = [];
      for(var i=0; i < code_lines.length; i++) {
        if(that.store.parameter_lines.indexOf(current_line) != -1) {
            code_lines[i] = hljs.highlight("python", code_lines[i]).value;
            var line_text = code_lines[i].replace(/\t/g, "&nbsp;&nbsp;&nbsp;").replace(/^[ \t]+/mg, html_space_replace);
            var line_div = {line_number: current_line, id: "line-number-" + current_line,
                            background: "background-color: transparent", color: "", show: true,
                            spanid: "span-bindings-line-" + current_line,
                            content: line_text, buttons: [], emptyid: "empty-line-" + current_line,
                            class: "code_listing_line", dict: {}, is_parameter: true,
                            parameters: that.store.parameter_values};
            lines_list.push(line_div);
        } else {
            code_lines[i] = hljs.highlight("python", code_lines[i]).value;
            var line_text = code_lines[i].replace(/\t/g, "&nbsp;&nbsp;&nbsp;").replace(/^[ \t]+/mg, html_space_replace);
            var line_div = {line_number: current_line, id: "line-number-" + current_line,
                            background: "background-color: transparent", color: "", show: true,
                            spanid: "span-bindings-line-" + current_line,
                            content: line_text, buttons: [], emptyid: "empty-line-" + current_line,
                            class: "code_listing_line", dict: {}};
            lines_list.push(line_div);
        }

        current_line++;
      }

      that.store.code_lines = lines_list;
      });
    });
  },
  methods:{
    downloadPDF : function(e) {
      e.preventDefault();
      var quality = 4;
      const filename  = 'plot.pdf';

      var svg = d3.select('#plot-svg-'+this.store.path_index)[0][0];
      var img = new Image();
      var serializer = new XMLSerializer();
      var svgStr = serializer.serializeToString(svg);

      img.src = 'data:image/svg+xml;base64,'+window.btoa(svgStr);
      $("#app").append(img);
      $("img").attr('id', "image-plot");

      html2canvas(document.querySelector('#image-plot'),
                {scale: quality}).then(canvas => {
        let pdf = new jsPDF('l', 'mm', [600,450]);
        pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0, 211, 150);
        pdf.save(filename);
        $("#image-plot").remove();
      });

      //window.location = "/download_plot/" + this.store.plot.current_hash;
    },
    toggleSuccessFilter : function(e) {
      e.preventDefault();
      this.store.plot.show_successes = !this.store.plot.show_successes;
      generate_plot(this);

    },
    toggleViolationFilter : function(e) {
      e.preventDefault();
      this.store.plot.show_violations = !this.store.plot.show_violations;
      generate_plot(this);
    },
    selectParameter : function(index) {
      this.store.path_index = index;
    },
    getClass : function(index) {
      if(this.store.path_index == index) {
        return "active"
      } else return "";
    }
  }


})

var app = new Vue({
    el : "#app"
});
