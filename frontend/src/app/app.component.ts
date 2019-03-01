import { Component } from '@angular/core';
import {ApiService, MetadataPayload, UserData} from './services/api.service';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ModalComponent } from './components/widgets';
import { HttpErrorResponse } from '@angular/common/http/src/response';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  constructor(public api: ApiService, public modal: NgbModal) {
    api.error$.subscribe(
      (error: HttpErrorResponse) => {
        const c = modal.open(ModalComponent);
        c.componentInstance.confirmText = 'OK';
      api.getMetadata().subscribe((result: MetadataPayload) => {
        c.componentInstance.dialog = `Sorry, an error has occured and the requested action has failed. If you think this should have worked, 
        please email ${result.metadata.supportEmail} with the following information`;
        c.componentInstance.metadata = `${error.error.message ? error.error.message : error.message}`;
        return c.result.then(() => {
          return true;
        }, () => {
          return false;
        });
      });
      }
    );
  }
}
