from DeepTrack.properties import Property, PropertyDict
from DeepTrack.Image import Image
from abc import ABC, abstractmethod
import os
import re
import numpy as np
import copy


class Feature(ABC):
    ''' Base feature class. 
    Features define a image generation process. Each feature takes an
    input image and alters it using the .get() method. Features can be
    added together using the + operator. In that case the left side of
    the + operator will be used as the input for the Feature on the 
    right. 

    Whenever a Feature is initiated, all keyword arguments passed to the
    constructor will be wrapped as a Distribution, and stored to the 
    `properties` field. When a Feature is resolved, a copy of this 
    field is sent as input to the get method, with each value replaced
    by the current_value field of the distribution.


    A typical lifecycle of a feature F is

    F.clear() 
        Clears the internal cache of the feature.
    F.update() 
        Recursively updates the feature and its parent(s).
    F.resolve() 
        Resolves the image generated by the feature.
    
    Properties
    ----------
    properties : dict
        A dict that contains all keyword arguments passed to the
        constructor wrapped a Distributions. A sampled copy of this
        dict is sent as input to the get function, and is appended
        to the properties field of the output image.
    cache: Image
        Stores the output of a `resolve` call. If this is not
        None, it will be returned instead of calling the get method.
    probability: number
        The probability of calling the get function of this feature
        during a `resolve()` call
    parent: Feature | ndarray
        During a `resolve()` call, this will serve as the input
        to the `get()` method. 
    
    Class Properties
    ----------------
    __name__
        Default name of the Feature.

    Methods
    -------
    clear() 
        Cleans up the tree after execution. Default behavior is
        to set the cache field to None and call clear() on
        the parent if it exists.
    update()
        If self is not in history, it calls the update method
        on the `properties` and `parent` and appends itself to
        the history list.
    resolve(image : ndarray, **kwargs)
        Uses the current_value of the properties field to
        generate an image using the .get() method. If the feature has
        a parent, the output of the resolve() call on the parent is 
        used as the input to the .get() method, otherwise an Image of
        all zeros is used.
    get_properties()
        Returns a copy of the properties field, with each value
        replaced by the current_value field.
    get_property(key : str)
        Returns the current_value of the field matching the key in properties.
    set_property(key : str, value : any)
        Sets the current_value of the field matching the key in properties.
    '''

    __name__ = "Unnamed feature"

    
    def __init__(self, **kwargs):
        ''' Constructor
        All keyword arguments passed to the base Feature class will be 
        wrapped as a Distribution, as such randomized during a update
        step.         
        '''
        properties = getattr(self, "properties", {})
        for key, value in kwargs.items():
            properties[key] = Property(value)  
        self.properties = PropertyDict(**properties)

        # Set up flags
        self.has_updated_since_last_resolve = False


    @abstractmethod
    def get(self, image, **kwargs):
        pass


    def resolve(self, image):
        properties = self.properties.current_value_dict()
        image = self.get(image, **properties)
        image.append(properties)
        self.has_updated_since_last_resolve = False
        return image


    def update(self):
        '''
        Updates the state of all properties.
        '''
        if not self.has_updated_since_last_resolve:
            self.properties.update()
        self.has_updated_since_last_resolve = True
        return self


    def sample(self):
        self.properties.update()
        return self
    

    def input_shape(self, shape):
        return shape


    def __add__(self, other):
        return FeatureBranch(self, other)
    

    def __mul__(self, other):
        return FeatureProbability(self, other)

    __rmul__ = __mul__


    def __pow__(self, other):
        return FeatureDuplicate(self, other)
    



class FeatureBranch(Feature):
    

    def __init__(self, F1, F2, **kwargs):
        super().__init__(feature_1=F1, feature_2=F2, **kwargs)
    

    def get(self, image, feature_1=None, feature_2=None, **kwargs):
        image = feature_1.resolve(image)
        image = feature_2.resolve(image)
        return image



class FeatureProbability(Feature):


    def __init__(self, feature, probability, **kwargs):
        super().__init__(
            feature = feature,
            probability=probability, 
            random_number=np.random.rand, 
            **kwargs)
    

    def get(self, image,
            feature=None, 
            probability=None, 
            random_number=None, 
            **kwargs):
        
        if random_number < probability:
            image = feature.resolve(image)

        return image


# TODO: Better name.
class FeatureDuplicate(Feature):


    def __init__(self, feature, num_duplicates, **kwargs):
        self.feature = feature
        super().__init__(
            num_duplicates=num_duplicates, #py > 3.6 dicts are ordered by insert time.
            features=lambda: [copy.deepcopy(feature).update() for _ in range(self.properties["num_duplicates"].current_value)], 
            **kwargs)


    def get(self, image, features=None, **kwargs):
        for feature in features:
            image = feature.resolve(image)
        return image


class Load(Feature):
    __name__ = "Load"
    def __init__(self,
                    path):
        self.path = path

        # Initiates the iterator
        super().__init__(loaded_image=next(self))


    def get(self, image, loaded_image=None, **kwargs):
        return image + loaded_image


    def __next__(self):
        while True:
            file = np.random.choice(self.get_files())
            image = np.load(file)
            np.random.shuffle(image)
            for i in range(len(image)):
                yield image[i]


    def setParent(self, F):
        raise Exception("The Load class cannot have a parent. For literal addition, use the Add class")


    def get_files(self):
        if os.path.isdir(self.path):
             return [os.path.join(self.path,file) for file in os.listdir(self.path) if os.path.isfile(os.path.join(self.path,file))]
        else:
            dirname = os.path.dirname(self.path)
            files =  os.listdir(dirname)
            pattern = os.path.basename(self.path)
            return [os.path.join(self.path,file) for file in files if os.path.isfile(os.path.join(self.path,file)) and re.match(pattern,file)]
        
# class Update(Feature):
#     def __init__(rules, **kwargs):
#         self.rules = rules
#         super().__init__(**kwargs)
    
#     def __call__(F):
#         return F + self

#     def __resolve__(self, shape, **kwargs):
        
