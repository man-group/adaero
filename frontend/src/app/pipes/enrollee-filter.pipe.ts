import { Pipe, PipeTransform } from '@angular/core';
import { EnrolleeItem } from '../services/api.service';

@Pipe({
  name: 'enrolleeFilter'
})
export class EnrolleeFilterPipe implements PipeTransform {

  transform(enrollees: EnrolleeItem[], criteria: string): any {
    const lowerCriteria = criteria.toLowerCase();
    return enrollees.filter((enrollee: EnrolleeItem) => {
      if (criteria.length < 3) {
        return true;
      } else if (enrollee.displayName.toLowerCase().indexOf(lowerCriteria) >= 0) {
        return true;
      } else if (enrollee.position.toLowerCase().indexOf(lowerCriteria) >= 0) {
        return true;
      } else if (enrollee.managerDisplayName.toLowerCase().indexOf(lowerCriteria) >= 0) {
        return true;
      } else if (enrollee.department.toLowerCase().indexOf(lowerCriteria) >= 0) {
        return true;
      } else {
        return false;
      }
    });
  }

}
