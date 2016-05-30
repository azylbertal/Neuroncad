#Overview

* This is an educational tool for system level neuroscience, powered by the [NEURON simulation environment](http://www.neuron.yale.edu/neuron/)
* May be used in linux-based development boards to create NEURON-based mobile robots

* Please report issues!


### Dependencies: ###


* NEURON with python (see: http://www.davison.webfactional.com/notes/installation-neuron-python/)
* [pygame](http://www.pygame.org/)
* [EzText](http://pygame.org/project-EzText-920-.html) is packaged with source

### Raspberry Pi: ###

* In order to compile NEURON on Raspberry Pi, first edit /nrn-7.4/src/Random123/features/gccfeatures.h and remove the following lines:

`#if !defined(__x86_64__) && !defined(__i386__) && !defined(__powerpc__)
#  error "This code has only been tested on x86 and powerpc platforms."
#include <including_a_nonexistent_file_will_stop_some_compilers_from_continuing_with_a_hopeless_task>
{ /* maybe an unbalanced brace will terminate the compilation */
 /* Feel free to try the Random123 library on other architectures by changing
 the conditions that reach this error, but you should consider it a
 porting exercise and expect to encounter bugs and deficiencies.
 Please let the authors know of any successes (or failures). */
#endif`

* Circuit:

![NeuronCAD_bb.png](https://bitbucket.org/repo/aqpXBj/images/3727378928-NeuronCAD_bb.png)