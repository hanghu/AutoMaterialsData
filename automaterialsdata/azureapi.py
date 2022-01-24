from image_util import normalize_coordinates, labeledImage, revert_coordinates_normalization 
from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry, Region
from msrest.authentication import ApiKeyCredentials

class AzureCVObjectDetectionAPI(object):
    """
     A warper class for simplifying the use of Azure Custom Vision Object Detections
    """
    

    def __init__(self, endpoint, key, resource_id, project_id=None, publish_iteration_name=None):
        """ 
        Class Constructor, takes the id from Azure Custom Vision. Here the key will
        be used both for training and predicition
        
        Args:
        ----
        endpoint: str
        key: str
        resource_id: str
        project_id: str
        """

        training_credentials   = ApiKeyCredentials(in_headers={"Training-key": key})
        prediction_credentials = ApiKeyCredentials(in_headers={"Prediction-key": key})
        
        self.trainer   = CustomVisionTrainingClient(endpoint, training_credentials)
        self.predictor = CustomVisionPredictionClient(endpoint, prediction_credentials)
        self.project_id = project_id
        self.publish_iteration_name = publish_iteration_name
        self.tags = {}

        if project_id is not None:
            for t in self.trainer.get_tags(project_id):
                self.tags[t.name] = t.id
        
        return

    def create_project(self, project_name):
        """
        Create a object detection project with name as project_name. Swith to this project
        when creation is complete.

        Args:
        ----
        project_name: str
        """
        # Find the object detection domain
        obj_detection_domain = next(domain for domain in self.trainer.get_domains() 
                                    if domain.type == "ObjectDetection" and domain.name == "General")

        # Create a new project
        print ("Creating project...")
        project = self.trainer.create_project(project_name, domain_id=obj_detection_domain.id)
        self.project_id = project.id

        return

    def create_tag(self, tag_name):
        """
        Create a tag at the current object detection project.

        Args:
        ----
        project_name: str
        """
        assert (self.project_id is not None)
        tag = self.trainer.create_tag(self.project_id, tag_name)
        self.tags[tag.name] = tag.id
        
        return

    def _upload_one_batch_training_images(self, tagged_images_with_regions):
        """
        Upload one batch (maximum 64) training images to Azure Custom Vision Object Detection.
        Only for internal use with in this class.
        
        Args:
        ----
        tagged_images_with_regions: list of ImageFileCreateEntry 
        
        """
        
        upload_result = self.trainer.create_images_from_files(
            self.project_id, ImageFileCreateBatch(images=tagged_images_with_regions))
        
        if not upload_result.is_batch_successful:
            print("Image batch upload failed.")
            for image in upload_result.images:
                print("Image status: ", image.status)

        return

    def upload_training_images(self, training_labeled_images):
        """
        Upload training images to Azure Custom Vision Object Detection.
        
        Args:
        ----
        training_lableded_images: list of labeledImage
        """
        assert (self.project_id is not None)
        
        print ("Adding images...")
        tagged_images_with_regions = []
        batch = 0

        for i in range(len(training_labeled_images)):
            if i > 0 and ( i % 64 ) == 0:
                batch += 1
                print("Adding images: batch ", batch)
                self._upload_one_batch_training_images(tagged_images_with_regions)
                tagged_images_with_regions = []

            # accumulating labels within one batch
            labeled_img = training_labeled_images[i]
            
            regions = []
            for t, labels in labeled_img.labels.items():
                
                if t not in self.tags.keys(): self.create_tag(t)

                tag_id = self.tags[t]
                
                for m in labels:
                    x,y,w,h = normalize_coordinates(m, labeled_img.shape)
                    regions.append(Region(tag_id=tag_id, left=x,top=y,width=w,height=h))
             
            with open(labeled_img.path, mode="rb") as image_contents:
                tagged_images_with_regions.append(
                    ImageFileCreateEntry(name=labeled_img.name, contents=image_contents.read(), regions=regions))
        
        batch += 1
        if len(tagged_images_with_regions) > 0: 
            print ("Adding images: batch ", batch)
            self._upload_one_batch_training_images(tagged_images_with_regions)

        return

    def predict_testing_images(self, testing_images, probality_threshold=0.5):
        
        for img in testing_images:
            with open(img.path, mode='rb') as test_data:
                results = self.predictor.detect_image(self.project_id, self.publish_iteration_name, test_data)
            
            for prediction in results.predictions:
                bb_boxes = {}
                if prediction.probability > probality_threshold:
                    if prediction.tag_name not in bb_boxes.keys():
                        bb_boxes[prediction.tag_name] = []

                    bb_boxes[prediction.tag_name].append([prediction.bounding_box.left, 
                                                          prediction.bounding_box.top, 
                                                          prediction.bounding_box.width, 
                                                          prediction.bounding_box.height])

                if len(bb_boxes) != 0:
                    for tag, labels in bb_boxes.items():
                        labels = [revert_coordinates_normalization(i, img.shape) for i in labels]
                        img.add_labels(tag, labels)

        
        return #testing_images
