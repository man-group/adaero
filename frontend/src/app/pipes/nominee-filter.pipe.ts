import { Pipe, PipeTransform } from '@angular/core';
import { NomineeItem } from '../services/api.service';

@Pipe({
  name: 'nomineeFilter'
})
export class NomineeFilterPipe implements PipeTransform {

  transform(nominees: NomineeItem[], criteria: string): any {
    const lowerCriteria = criteria.toLowerCase();
    return nominees.filter((nominee: NomineeItem) => {
      if (criteria.length < 3) {
        return true;
      } else if (nominee.displayName.toLowerCase().indexOf(lowerCriteria) >= 0) {
        return true;
      } else if (nominee.position.toLowerCase().indexOf(lowerCriteria) >= 0) {
        return true;
      } else if (nominee.managerDisplayName.toLowerCase().indexOf(lowerCriteria) >= 0) {
        return true;
      } else if (nominee.department.toLowerCase().indexOf(lowerCriteria) >= 0) {
        return true;
      } else {
        return false;
      }
    });
  }

}
