# Changelog

## 0.0.7
* `GroupWorkflow.group_members` implemented
  * `group_workflow_group_members` is config key for queue name
* `GroupWorkflow.get_groups` implemented
  * `group_workflow_get_groups` is config key for queue name
* implemented cli switch for generating the database `-g`
## 0.0.6
* `logger.exception` for exception logging isntead of print
## 0.0.5
* BUGFIX: _create_user only takes KW arguments which i forgot...
## 0.0.4
* Formating...
## 0.0.3
* Reworked the wrapper to use AMQPService class from amqp_helper
* added basic Exception Handler
## 0.0.2
* This version mainly adds Documentation to some Functions. Nothing more Nothing less.
## 0.0.1
Initial Version
* can start programm
* endpoints are callable over AMQP