Based on the generated use case statement, create a todo list in the
form of user stories required to fulfill it.

Use the user story structure:

“As a [persona], I [want to], [so that].”

Under each user story, create a list of scenarios in the form of tiny
feature slices each with a matching gherkin-style acceptance
test.

Using the evolutionary vertical feature slicing approach, each
slice should deliver a tiny bit of value to the
user end-to-end and builds on previous tasks.

Intermediate shortcuts can be taken where necessary
e.g. hardcoding some values, or using a flat-file for storage
if subsequent tasks will replace them with production ready
equivalents.

Create a todo list representing the user stories and related
scenarios as feature slices.

# VERY IMPORTANT
- Use markdown
- Each user story should list related scenarios
- Each scenario should represent a thin vertical feature slice 
  that delivers some value to an end user
  (consumer, operator or backend staff)
- We should be able to change each user story's status from todo -> in
  progress -> done
- Each user story should have a number id
