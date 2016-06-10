window.App = Ember.Application.create();

// App.Router.map(function() {
//   this.resource('application', {path: '/'});
// });

App.ApplicationController = Ember.Controller.extend({
  queryParams: ['category'],
  category: 1,
});