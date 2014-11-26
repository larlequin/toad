from generic.generictask import GenericTask
from modules import util, mriutil
import os

__author__ = 'desmat'


class Masking(GenericTask):


    def __init__(self, subject):
        GenericTask.__init__(self, subject, 'registration')


    def implement(self):

        aparcAseg = self.getImage(self.dependDir,"aparc_aseg", "resample")
        anatBrainResample = self.getImage(self.dependDir,'anat', ['brain','resample'] )

        anatBrainWMResample = self.getImage(self.dependDir, 'anat', ['brain','wm','resample'])
        self.__createMask(anatBrainWMResample)

        extended = self.getTarget('anat', 'extended','nii')
        self.info("Add %s and %s images together in order to create the ultimate image"%(anatBrainResample, aparcAseg))
        mriutil.fslmaths(anatBrainResample, extended, 'add', aparcAseg)
        self.__createMask(extended)

        self.__createMask(aparcAseg)

        #produce optionnal mask
        if self.get("start_seeds").strip():
            self.__createRegionMaskFromAparcAseg(aparcAseg, 'start')
        if self.get("stop_seeds").strip():
            self.__createRegionMaskFromAparcAseg(aparcAseg, 'stop')
        if self.get("exclude_seeds").strip():
            self.__createRegionMaskFromAparcAseg(aparcAseg, 'exclude')

        #Launch act_anat_prepare_freesurfer
        act = self.__actAnatPrepareFreesurfer(aparcAseg)

        #extract the white matter mask from the act
        whiteMatterAct = self.__extractWhiteMatterFromAct(act)

        #Produces a mask image suitable for seeding streamlines from the grey matter - white matter interface
        seed_gmwmi = self.__launch5tt2gmwmi(act)


    def __createRegionMaskFromAparcAseg(self, source, operand):
        option = "%s_seeds"%operand

        self.info("Extract %s regions from %s image"%(operand, source))
        regions = util.arrayOfInteger(self.get( option))
        self.info("Regions to extract: %s"%(regions))

        target = self.getTarget(source, [operand, "extract"])
        structures = mriutil.extractFreesurferStructure(regions, source, target)
        self.__createMask(structures)

    def __actAnatPrepareFreesurfer(self, source):
        """Create a five-tissue-type (5TT) segmented image in a format appropriate for ACT

        Args:
            source:  A segmented T1 image from FreeSurfer

        Returns:
            A five-tissue-type (5TT) segmented image in a format appropriate for AC
        """

        tmp = os.path.join(self.workingDir, "tmp.nii")
        target = self.getTarget(source, 'act')
        self.info("Starting act_anat_prepare_freesurfer creation from mrtrix on %s"%source)

        cmd = "act_anat_prepare_freesurfer %s %s"%(source, tmp)
        self.launchCommand(cmd)

        self.info("renaming %s to %s"%(tmp, target))
        os.rename(tmp, target)

        return target


    def __extractWhiteMatterFromAct(self, source):
        """Extract the white matter part from the act

        Args:
            An act image

        Returns:
            the resulting file filename

        """
        target = self.getTarget(source, ["wm", "mask"])
        self.info(mriutil.extractSubVolume(source,
                                target,
                                self.get('act_extract_at_axis'),
                                self.get("act_extract_at_coordinate"),
                                self.getNTreadsMrtrix()))
        return target


    def __launch5tt2gmwmi(self, source):
        """Generate a mask image appropriate for seeding streamlines on the grey
           matter - white matter interface

        Args:
            source: the input 5TT segmented anatomical image

        Returns:
            the output mask image
        """

        tmp = os.path.join(self.workingDir, "tmp.nii")
        target = self.getTarget(source, "5tt2gmwmi")
        self.info("Starting 5tt2gmwmi creation from mrtrix on %s"%source)

        cmd = "5tt2gmwmi %s %s -nthreads %s -quiet"%(source, tmp, self.getNTreadsMrtrix())
        self.launchCommand(cmd)

        self.info("renaming %s to %s"%(tmp, target))
        os.rename(tmp, target)

        return target


    def __createMask(self, source):
        self.info("Create mask from %s images"%(source))
        mriutil.fslmaths(source, self.getTarget(source, 'mask'), 'bin')


    def meetRequirement(self):

        images = {'resampled parcellation':self.getImage(self.dependDir,"aparc_aseg", "resample"),
                    'brain extracted, white matter segmented, resampled high resolution':self.getImage(self.dependDir,'anat',['brain','wm','resample']),
                    'brain extracted, resampled high resolution':self.getImage(self.dependDir,'anat',['brain','resample'])}

        return self.isAllImagesExists(images)


    def isDirty(self, result = False):

        images ={'aparc anatomically constrained tractography': self.getImage(self.workingDir,"aparc_aseg", ["resample","mask"]),
                    'aparc_aseg mask': self.getImage(self.workingDir,"aparc_aseg", ["resample", "mask"]),
                    'anatomically constrained tractography': self.getImage(self.workingDir,"aparc_aseg", ["act"]),
                    'white segmented mask': self.getImage(self.workingDir,"aparc_aseg", ["act", "wm", "mask"]),
                    'seeding streamlines 5tt2gmwmi': self.getImage(self.workingDir, "aparc_aseg", "5tt2gmwmi"),
                    'high resolution, brain extracted, white matter segmented, resampled mask': self.getImage(self.workingDir, 'anat', ['brain', 'wm', 'resample', 'mask']),
                    'ultimate extended mask': self.getImage(self.workingDir, 'anat',['extended','mask'])}

        if self.config.get('masking', "start_seeds").strip() != "":
            images['high resolution, start, brain extracted mask'] = self.getImage(self.workingDir, 'aparc_aseg', ['resample', 'start', 'extract', 'mask'])
            images['high resolution, start, brain extracted'] = self.getImage(self.workingDir, 'aparc_aseg', ['resample', 'start', 'extract'])

        if self.config.get('masking', "stop_seeds").strip() != "":
            images['high resolution, stop, brain extracted mask'] = self.getImage(self.workingDir, 'aparc_aseg', ['resample', 'stop', 'extract', 'mask'])
            images['high resolution, stop, brain extracted'] = self.getImage(self.workingDir, 'aparc_aseg', ['resample', 'stop', 'extract'])

        if self.config.get('masking', "exclude_seeds").strip() != "":
            images['high resolution, excluded, brain extracted, mask'] = self.getImage(self.workingDir, 'aparc_aseg', ['resample', 'exclude', 'extract', 'mask'])
            images['high resolution, excluded, brain extracted']= self.getImage(self.workingDir, 'aparc_aseg', ['resample', 'exclude', 'extract'])

        if self.isSomeImagesMissing(images):
            result = True

        return result

