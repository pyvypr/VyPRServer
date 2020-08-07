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
    }
};


var generate_plot = function(root_obj) {
    var that = root_obj;

    // send a request to the server to get the plot data
    axios.get('/get_plot_data_from_hash/' + Store.plot.current_hash).then(function(response){
      console.log(response.data);
      // prepare data for plotting
      var data = response.data.data;
      var type = response.data.description.type;
      Store.plot.type = type;
      that.store.plot.type = type;
      console.log(type);

      console.log(response.data);

      if (type == "severity" || type == "observation" || type=="between-severity" ||
          type == "between-observation"){
          var myData = [{key: 'group 1', values: []}];
          for (var i=0; i<data["x"].length; i++){
            var value = data[type][i];

            if(type == "severity" || type == "between-severity") {
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
            } else {
              color = "blue";
            }
            //value = ( value >= 0 )? value : -Math.abs(Math.log(-value));
            myData[0].values.push({label: new Date(Date.parse(data["x"][i])),
                                  value: value,
                                  color: color});
          }
      }
      if (type == "mixed-severity" || type == "mixed-observation"){
          if(type == "mixed-severity") {
            var myData = [{key: 'group 1', values: []}];
            for (var i=0; i<data["x1"].length; i++){
              var value = data[type][i];
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
              myData[0].values.push({label: new Date(Date.parse(data["x1"][i])),
                                    value: value,
                                    color: color});
            }
          } else {
            var myData = [{key: 'subatom 0', values: []}, {key: 'subatom 1', values: []}];
            for (var i=0; i<data["x1"].length; i++){
              var value1 = data[type+"-1"][i];
              var value2 = data[type+"-2"][i]

              myData[0].values.push({label: new Date(Date.parse(data["x1"][i])),
                                     value: value1});
              myData[1].values.push({label: new Date(Date.parse(data["x1"][i])),
                                     value: value2});
            }
          }
      }

      that.$root.$emit("plot-data-ready", myData);

    });
};

Vue.component("plot", {
  template: `<div id="plot-wrapper" class="plot">
  <p><a href="#" @click="downloadPDF($event)">Download PDF</a></p>
  <!--<div id="plot-description" v-html="this.description"></div>-->
  <div id="plot-filters" v-if="is_severity_plot">Filters:
    <a href="#" id="violations" class="filter" v-bind:class="{active : violationFilterActive}"
      @click="toggleViolationFilter($event)">Violations</a>
    <a href="#" id="successes" class="filter" v-bind:class="{active : successFilterActive}"
      @click="toggleSuccessFilter($event)">Successes</a>
  </div>
  <svg id="plot-svg" height="800px" width="1250px"></svg>
  </div>`,
  props : ["hash"],
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
      return this.store.plot.type == "severity" || this.store.plot.type == "between-severity" || this.store.plot.type == "mixed-severity";
    },
    is_mixed_observation_plot : function() {
      return this.store.plot.type == "mixed-observation";
    }
  },
  mounted(){
    // store the hash
    this.store.plot.current_hash = this.hash;
    // generate the plot based on the hash
    generate_plot(this);
    this.store.plot.type = Store.plot.type;
    var that = this;
    this.$root.$on("plot-data-ready", function(data_array){
      nv.addGraph(function() {

        var chart = nv.models.multiBarChart()
          .x(function(d) { return d.label })
          .y(function(d) { return d.value })
          .reduceXTicks(true)    //alternatively, use staggering or rotated labels to prevent overlapping
          .showControls(false)
          .showLegend(that.is_mixed_observation_plot)
          .color(["#2b5fed", "#f5b52c"]);

        // omitting date from time format - moslty the difference is in seconds
        var y_label = that.is_severity_plot ? 'Verdict severity' : 'Observation';
        chart.xAxis
          .axisLabel('Time of observation')
          .tickFormat(function(d) { return d3.time.format('%H:%M:%S')(new Date(d)); });
        chart.yAxis
          .axisLabel(y_label)
          .tickFormat(d3.format('.02f'))
          .showMaxMin(true);

        d3.select('#plot-svg')
          .datum(data_array)
          .call(chart);

        nv.utils.windowResize(chart.update);

        // set initial size
        chart.update();

        return chart;
      });
    })
  },
  methods:{
    downloadPDF : function(e) {
      e.preventDefault();
      var quality = 3; // can be improved but we don't want the pdf to take up too much memory
      const filename  = 'plot.pdf';

      // converting the svg to img to prevent the labels from doubling when converting to canvas
      var svg = d3.select("svg")[0][0];
      var img = new Image();
      var serializer = new XMLSerializer();
      var svgStr = serializer.serializeToString(svg);

      // adding the image to the dom so it can be copied to canvas (works kind of like a screenshot)
      img.src = 'data:image/svg+xml;base64,'+window.btoa(svgStr);
      $("#app").append(img);
      $("img").attr('id', "image-plot");

      // draw image on canvas and add the canvas to pdf (couldn't be done directly with svg)
      html2canvas(document.querySelector('#image-plot'),
								{scale: quality}).then(canvas => {
			  let pdf = new jsPDF('l', 'mm', [600,450]);
			  pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0, 211, 150);
			  pdf.save(filename);
        $("#image-plot").remove();
      });
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
    }
  }


})

var app = new Vue({
    el : "#app"
});
