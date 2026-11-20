import {calculateExample, exampleScenarios} from './labor-example.js';
import {demoAdapter} from './labor-review-fixture.js';
import {breakdown, mountLaborReview} from './labor-review.js';

const reviewId = new URLSearchParams(location.search).get('review');
mountLaborReview(document.querySelector('#labor-demo'), demoAdapter(reviewId));

const scenarios = document.querySelector('#labor-scenarios');
const picker = document.querySelector('#labor-scenario');
const output = document.querySelector('#scenario-output');
const update = document.querySelector('#scenario-update');
for (const {id, name} of exampleScenarios) picker.add(new Option(name, id));

picker.addEventListener('change', () => {
  const scenario = exampleScenarios.find(({id}) => id === picker.value);
  output.innerHTML = scenario ? breakdown({
    inputs: scenario.inputs,
    metrics: calculateExample(scenario.inputs),
    source: `Fictional scenario · ${scenario.name}`
  }) : '';
  update.textContent = scenario ? `Labor variance updated for ${scenario.name}.` : '';
});
scenarios.hidden = false;
