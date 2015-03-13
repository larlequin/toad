from lib.generictask import GenericTask
from lib import mriutil
import os

__author__ = 'desmat'

class Registration(GenericTask):


    def __init__(self, subject):
        GenericTask.__init__(self, subject, 'preprocessing', 'parcellation')


    def implement(self):

        b0 = self.getImage(self.dependDir, 'b0','upsample')
        b02x2x2 = self.getImage(self.dependDir, 'b0','2x2x2')

        anat = self.getImage(self.parcellationDir, 'anat', 'freesurfer')
        anatBrain = self.getImage(self.preprocessingDir ,'anat', 'brain')
        aparcAsegFile =  self.getImage(self.parcellationDir, "aparc_aseg")
        rhRibbon = self.getImage(self.parcellationDir, "rh_ribbon")
        lhRibbon = self.getImage(self.parcellationDir, "lh_ribbon")
        brodmann = self.getImage(self.parcellationDir, "brodmann")

        b0ToAnatMatrix = self.__computeResample(b0, anat)
        b0ToAnatMatrixInverse = mriutil.invertMatrix(b0ToAnatMatrix, self.buildName(b0ToAnatMatrix, 'inverse', 'mat'))

        self.__applyResampleFsl(anat, b0, b0ToAnatMatrixInverse, self.buildName(anat, "resample"))
        mrtrixMatrix = self.__transformMatrixFslToMrtrix(anat, b0, b0ToAnatMatrixInverse)

        self.__applyResampleFsl(anatBrain, b0, b0ToAnatMatrixInverse, self.buildName(anatBrain, "resample"))
        self.__applyRegistrationMrtrix(aparcAsegFile, mrtrixMatrix)
        self.__applyResampleFsl(aparcAsegFile, b0, b0ToAnatMatrixInverse, self.buildName(aparcAsegFile, "resample"))


        b02x2x2ToAnatMatrix = self.__computeResample(b02x2x2, anat)
        b02x2x2ToAnatMatrixInverse = mriutil.invertMatrix(b02x2x2ToAnatMatrix, self.buildName(b02x2x2ToAnatMatrix, 'inverse', 'mat'))
        self.__applyResampleFsl(aparcAsegFile, b02x2x2, b02x2x2ToAnatMatrixInverse, self.buildName(aparcAsegFile, "2x2x2"))
        self.__applyResampleFsl(anatBrain, b02x2x2, b02x2x2ToAnatMatrixInverse, self.buildName(anatBrain, "2x2x2"))


        brodmannRegister = self.__applyRegistrationMrtrix(brodmann, mrtrixMatrix)
        self.__applyResampleFsl(brodmann, b0, b0ToAnatMatrixInverse, self.buildName(brodmann, "resample"))

        lhRibbonRegister = self.__applyRegistrationMrtrix(lhRibbon, mrtrixMatrix)
        rhRibbonRegister = self.__applyRegistrationMrtrix(rhRibbon, mrtrixMatrix)

        self.__applyResampleFsl(lhRibbon, b0, b0ToAnatMatrixInverse, self.buildName(lhRibbon, "resample"))
        self.__applyResampleFsl(rhRibbon, b0, b0ToAnatMatrixInverse, self.buildName(rhRibbon, "resample"))

        brodmannLRegister =  self.buildName(brodmannRegister, "left_hemisphere")
        brodmannRRegister =  self.buildName(brodmannRegister, "right_hemisphere")

        self.__multiply(brodmannRegister, lhRibbonRegister, brodmannLRegister)
        self.__multiply(brodmannRegister, rhRibbonRegister, brodmannRRegister)


    def __multiply(self, source, ribbon, target):

        cmd = "mrcalc {} {} -mult {} -quiet".format(source, ribbon, target)
        self.launchCommand(cmd)
        return target


    def __computeResample(self, source, reference):
        """Register an image with symmetric normalization and mutual information metric

        Returns:
            return a file containing the resulting transformation
        """
        self.info("Starting registration from fsl")
        name = os.path.basename(source).replace(".nii","")
        target = self.buildName(name, "transformation","")
        matrix = self.buildName(name, "transformation", ".mat")
        cmd = "flirt -in {} -ref {} -cost {} -omat {} -out {}".format(source, reference, self.get('cost'), matrix, target)
        self.launchCommand(cmd)
        return matrix


    def __applyResampleFsl(self, source, reference, matrix, target):
        """Register an image with symmetric normalization and mutual information metric

        Returns:
            return a file containing the resulting transformation
        """
        self.info("Starting registration from fsl")
        #name = os.path.basename(source).replace(".nii","")
        #target = self.buildName(name, "resample")
        cmd = "flirt -in {} -ref {} -applyxfm -init {} -out {}".format(source, reference, matrix, target)
        self.launchCommand(cmd)
        return target


    def __transformMatrixFslToMrtrix(self, source, b0, matrix ):
        target = self.buildName(matrix, "mrtrix", ".mat")
        cmd = "transformcalc -flirt_import {} {} {} {} -quiet".format(source, b0, matrix, target)
        self.launchCommand(cmd)
        return target


    def __applyRegistrationMrtrix(self, source , matrix):
        target = self.buildName(source, "register")
        cmd = "mrtransform  {} -linear {} {} -quiet".format(source, matrix, target)
        self.launchCommand(cmd)
        return target


    def meetRequirement(self):

        images = {'high resolution': self.getImage(self.parcellationDir, 'anat', 'freesurfer'),
                  'freesurfer anatomical brain extracted': self.getImage(self.dependDir, 'anat', 'brain'),
                  'b0 upsampled': self.getImage(self.dependDir, 'b0', 'upsample'),
                  'b0 2x2x2': self.getImage(self.dependDir, 'b0','2x2x2'),
                  'parcellation': self.getImage(self.parcellationDir, 'aparc_aseg'),
                  'right hemisphere ribbon': self.getImage(self.parcellationDir, 'rh_ribbon'),
                  'left hemisphere ribbon': self.getImage(self.parcellationDir, 'lh_ribbon'),
                  'brodmann': self.getImage(self.parcellationDir, 'brodmann')}
        return self.isAllImagesExists(images)


    def isDirty(self, result = False):
        images = {'anatomical brain resampled': self.getImage(self.workingDir,'anat', ['brain', 'resample']),
                  'anatomical resampled': self.getImage(self.workingDir,'anat','resample'),
                  'anatomical 2x2x2 brain for dtifit': self.getImage(self.workingDir,'anat', ['brain', '2x2x2']),
                  'parcellation 2x2x2 for dtifit': self.getImage(self.workingDir,'aparc_aseg', '2x2x2'),
                  'parcellation resample': self.getImage(self.workingDir,'aparc_aseg', 'resample'),
                  'parcellation register': self.getImage(self.workingDir,'aparc_aseg', 'register'),
                  'brodmann register left hemisphere': self.getImage(self.workingDir,'brodmann', ['register', "left_hemisphere"]),
                  'brodmann register right hemisphere': self.getImage(self.workingDir,'brodmann', ['register', "right_hemisphere"])}
        return self.isSomeImagesMissing(images)